#!/usr/bin/env python3
"""Local stdio MCP for an existing SageMath installation."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
import time
from typing import Annotated

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

ROOT = Path(__file__).resolve().parent
OUTPUT_BYTES = 80_000
MAX_RESULT_BYTES = 1_000_000
RUNS = asyncio.Semaphore(2)
mcp = FastMCP(
    "SageMath",
    instructions=(
        "Use sage_info to check the local SageMath runtime and sage_execute for exact "
        "arithmetic, algebra, calculus, number theory, matrices, and Sage scripts. "
        "Each call has a fresh namespace with sage.all and symbolic x available. "
        "Sage syntax, including ^, exact fractions, and R.<t> = QQ[], is preparsed. "
        "Put the desired result in the final expression, or print it. Variables and "
        "temporary files do not persist between calls. Execution has local Python "
        "permissions; use only code appropriate to the user's request."
    ),
    log_level="WARNING",
)


def reply(data: dict) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
        structuredContent=data,
        isError=not data.get("ok", False),
    )


def sage_executable() -> str:
    configured = os.environ.get("SAGE_EXECUTABLE")
    executable = shutil.which(configured or "sage")
    if not executable:
        raise FileNotFoundError(
            "SageMath was not found. Set SAGE_EXECUTABLE to the absolute sage executable."
        )
    return executable


def worker_environment(directory: Path, executable: str) -> dict[str, str]:
    # Do not copy unrelated service credentials into calculation processes.
    names = ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR")
    env = {key: os.environ[key] for key in names if key in os.environ}
    env.update(
        PATH=str(Path(executable).parent) + os.pathsep + os.defpath,
        DOT_SAGE=str(directory / "dot-sage"),
        IPYTHONDIR=str(directory / "ipython"),
        MPLCONFIGDIR=str(directory / "matplotlib"),
        MPLBACKEND="Agg",
        PYTHONNOUSERSITE="1",
        PYTHONUNBUFFERED="1",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
    )
    return env


async def capture(stream: asyncio.StreamReader) -> tuple[str, bool]:
    """Drain all output while retaining only a bounded prefix in memory."""
    kept = bytearray()
    truncated = False
    while block := await stream.read(8192):
        remaining = OUTPUT_BYTES - len(kept)
        kept.extend(block[:remaining])
        truncated |= len(block) > remaining
    return kept.decode("utf-8", errors="replace"), truncated


def kill_group(process: asyncio.subprocess.Process) -> None:
    # Kill Sage's child programs too, even if the worker has already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


async def calculate(code: str, timeout_seconds: float, include_latex: bool) -> dict:
    started = time.monotonic()
    try:
        executable = sage_executable()
    except FileNotFoundError as exc:
        return {"ok": False, "error": {"type": "ConfigurationError", "message": str(exc)}}
    async with RUNS:
        with tempfile.TemporaryDirectory(prefix="sagemath-mcp-") as temporary:
            directory = Path(temporary)
            result_path = directory / "result.json"
            request_path = directory / "request.json"
            request_path.write_text(json.dumps({"code": code, "include_latex": include_latex}))
            try:
                process = await asyncio.create_subprocess_exec(
                    executable, "-python", str(ROOT / "worker.py"),
                    str(request_path), str(result_path),
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=directory,
                    env=worker_environment(directory, executable),
                    start_new_session=True,
                )
            except OSError as exc:
                return {"ok": False, "error": {"type": "StartupError", "message": str(exc)}}
            stdout_task = asyncio.create_task(capture(process.stdout))
            stderr_task = asyncio.create_task(capture(process.stderr))
            timed_out = False
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout_seconds)
            except TimeoutError:
                timed_out = True
            finally:
                # Also runs on MCP cancellation. Never leave a computation running.
                kill_group(process)
                with anyio.CancelScope(shield=True):
                    await process.wait()
                    stdout, stdout_truncated = await stdout_task
                    stderr, stderr_truncated = await stderr_task
            if timed_out:
                data = {"ok": False, "error": {
                    "type": "TimeoutError",
                    "message": f"SageMath exceeded the {timeout_seconds:g} second time limit.",
                }}
            elif not result_path.is_file():
                data = {"ok": False, "error": {
                    "type": "WorkerError",
                    "message": f"SageMath exited without a result (exit code {process.returncode}).",
                }}
            else:
                try:
                    if result_path.stat().st_size > MAX_RESULT_BYTES:
                        raise ValueError("SageMath result exceeds the transport limit.")
                    data = json.loads(result_path.read_text())
                    if not isinstance(data, dict) or not isinstance(data.get("ok"), bool):
                        raise ValueError("Invalid SageMath worker result.")
                except (OSError, ValueError) as exc:
                    data = {"ok": False, "error": {"type": "WorkerError", "message": str(exc)}}
            data.update(
                stdout=stdout, stderr=stderr,
                stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
                elapsed_seconds=round(time.monotonic() - started, 3),
            )
            return data


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
async def sage_info() -> CallToolResult:
    """Check that SageMath runs and return its version and supported execution settings."""
    data = await calculate("import sage.version\nsage.version.version", 30, False)
    if data.get("ok"):
        data.update(
            sage_version=data.pop("result"), sage_executable=sage_executable(),
            server_version="1.0.0", transport="stdio", state="fresh process per call",
            default_timeout_seconds=30, maximum_timeout_seconds=120,
            maximum_code_characters=65_536, output_limit_bytes_per_stream=OUTPUT_BYTES,
        )
    return reply(data)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True))
async def sage_execute(
    code: Annotated[str, Field(min_length=1, max_length=65_536, description="Sage expression or multiline script. The final expression is returned; prints are captured.")],
    timeout_seconds: Annotated[float, Field(ge=1, le=120, description="Wall-clock limit including Sage startup, in seconds.")] = 30,
    include_latex: bool = True,
) -> CallToolResult:
    """Execute local SageMath code. Supports ^, exact fractions, and R.<x> syntax.

    Each call imports sage.all and defines symbolic x in a fresh process. Returns
    result text, type, optional LaTeX, stdout/stderr, and structured errors.
    Working files are temporary; save to an explicit absolute path to keep files.
    Code runs with local user permissions, including filesystem and network access.
    """
    return reply(await calculate(code, timeout_seconds, include_latex))


if __name__ == "__main__":
    mcp.run(transport="stdio")
