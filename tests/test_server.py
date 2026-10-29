"""Safeguard tests; fake Sage validates orchestration, not Sage mathematics."""
import asyncio
import json
from datetime import timedelta
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import server
import worker

ROOT = Path(__file__).resolve().parents[1]
FAKE = '''#!PYTHON
import json, os, subprocess, sys, time
from pathlib import Path
request = json.loads(Path(sys.argv[-2]).read_text())
code = request['code']
result = Path(sys.argv[-1])
if code == 'sleep':
    print(os.getpid(), flush=True)
    time.sleep(10)
elif code == 'flood':
    os.write(1, b'x' * 100000)
    os.write(2, b'y' * 100000)
elif code == 'invalid':
    result.write_text('[]')
    sys.exit(0)
elif code == 'oversized':
    result.write_text('x' * 1000001)
    sys.exit(0)
elif code == 'missing':
    sys.exit(2)
elif code.startswith('cancel:'):
    Path(code.split(':', 1)[1]).write_text(str(os.getpid()))
    time.sleep(10)
elif code.startswith('child:'):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
    Path(code.split(':', 1)[1]).write_text(str(child.pid))
    time.sleep(10)
result.write_text(json.dumps({'ok': True, 'result': '42'}))
'''


class Safeguards(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sage test ')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.fake = self.path / 'fake sage'
        self.fake.write_text(FAKE.replace('PYTHON', sys.executable, 1))
        self.fake.chmod(0o755)
        self.env = patch.dict(os.environ, SAGE_EXECUTABLE=str(self.fake))
        self.env.start()
        self.addCleanup(self.env.stop)
        # Each isolated test runs its own event loop.
        server.RUNS = asyncio.Semaphore(2)

    async def test_missing_runtime(self):
        with patch.dict(os.environ, SAGE_EXECUTABLE=str(self.path / 'absent')):
            result = await server.calculate('1', 1, False)
        self.assertEqual(result['error']['type'], 'ConfigurationError')

    async def test_startup_error(self):
        self.fake.write_text('#!/nonexistent/interpreter\n')
        result = await server.calculate('1', 1, False)
        self.assertEqual(result['error']['type'], 'StartupError')

    async def test_stream_limits_and_recovery(self):
        result = await server.calculate('flood', 2, False)
        self.assertTrue(result['ok'])
        for name in ('stdout', 'stderr'):
            self.assertEqual(len(result[name].encode()), server.OUTPUT_BYTES)
            self.assertTrue(result[name + '_truncated'])
        self.assertTrue((await server.calculate('1', 2, False))['ok'])

    async def test_invalid_worker_results(self):
        for code in ('invalid', 'oversized', 'missing'):
            with self.subTest(code=code):
                result = await server.calculate(code, 2, False)
                self.assertEqual(result['error']['type'], 'WorkerError')

    async def test_timeout_and_recovery(self):
        result = await asyncio.wait_for(server.calculate('sleep', 0.15, False), 3)
        self.assertEqual(result['error']['type'], 'TimeoutError')
        pid = int(result['stdout'].strip())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertTrue((await server.calculate('1', 2, False))['ok'])

    async def wait_for_pid(self, file):
        for _ in range(100):
            if file.exists():
                return int(file.read_text())
            await asyncio.sleep(0.01)
        self.fail('worker did not start')

    async def test_cancellation_reaps_worker(self):
        marker = self.path / 'pid'
        task = asyncio.create_task(server.calculate('cancel:' + str(marker), 10, False))
        pid = await self.wait_for_pid(marker)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 3)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    @unittest.skipUnless(sys.platform == 'linux', 'uses /proc to distinguish zombie children')
    async def test_timeout_kills_process_group(self):
        marker = self.path / 'child'
        result = await asyncio.wait_for(server.calculate('child:' + str(marker), 0.3, False), 3)
        self.assertEqual(result['error']['type'], 'TimeoutError')
        pid = int(marker.read_text())
        # Orphan zombies may wait for the host's init process to reap them.
        stat = Path(f'/proc/{pid}/stat')
        self.assertTrue(not stat.exists() or stat.read_text().split(') ')[1].startswith('Z'))

    def test_environment_excludes_credentials(self):
        with patch.dict(os.environ, EXAMPLE_SECRET='do-not-inherit'):
            env = server.worker_environment(self.path, str(self.fake))
        self.assertNotIn('EXAMPLE_SECRET', env)
        self.assertEqual(env['OMP_NUM_THREADS'], '1')
        self.assertEqual(env['DOT_SAGE'], str(self.path / 'dot-sage'))

    def test_worker_text_limit(self):
        self.assertEqual(worker.limited('z' * 20001), ('z' * 20000, True))
        self.assertEqual(worker.limited('ok'), ('ok', False))

    async def test_mcp_validation_and_launcher(self):
        parameters = StdioServerParameters(
            command='/bin/bash', args=[str(ROOT / 'launch.sh')], cwd=str(self.path),
            env={'SAGE_EXECUTABLE': str(self.fake), 'SAGEMATH_MCP_PYTHON': sys.executable},
        )
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=5)) as session:
                self.assertEqual((await session.initialize()).serverInfo.name, 'SageMath')
                tools = {t.name: t for t in (await session.list_tools()).tools}
                self.assertEqual(set(tools), {'sage_info', 'sage_execute'})
                self.assertTrue(tools['sage_execute'].annotations.destructiveHint)
                self.assertTrue(tools['sage_execute'].annotations.openWorldHint)
                for arguments in ({}, {'code': ''}, {'code': 'x' * 65537},
                                  {'code': '1', 'timeout_seconds': 0},
                                  {'code': '1', 'timeout_seconds': 121}):
                    self.assertTrue((await session.call_tool('sage_execute', arguments)).isError)
                result = await session.call_tool('sage_execute', {'code': '1'})
                self.assertFalse(result.isError)
                self.assertEqual(result.structuredContent['result'], '42')
                self.assertTrue((await session.call_tool('sage_info', {})).structuredContent['ok'])
