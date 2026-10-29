#!/usr/bin/env python3
"""End-to-end MCP tests; accepts the installed launch.sh to test the real package."""
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(launcher, report_path):
    records = []

    def record(name, passed, details=None):
        records.append({"name": name, "passed": bool(passed), "details": details})
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)

    parameters = StdioServerParameters(
        command="/bin/bash", args=[str(launcher)],
        env={key: os.environ[key] for key in ("SAGE_EXECUTABLE", "SAGEMATH_MCP_PYTHON") if key in os.environ},
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=45)) as session:
            initialized = await session.initialize()
            record("MCP initialization", initialized.serverInfo.name == "SageMath", initialized.model_dump(mode="json"))
            tools = (await session.list_tools()).tools
            record("MCP tool discovery", {t.name for t in tools} == {"sage_info", "sage_execute"})
            record("Code execution permission annotations", next(t for t in tools if t.name == "sage_execute").annotations.readOnlyHint is False)

            async def call(name, code=None, *, expected=None, error=None, **arguments):
                response = await session.call_tool("sage_info" if code is None else "sage_execute", {} if code is None else {"code": code, **arguments})
                data = response.structuredContent or {}
                passed = data.get("ok") is (error is None) and response.isError is (error is not None)
                if expected is not None:
                    passed &= data.get("result") == expected
                if error:
                    passed &= data.get("error", {}).get("type") == error
                record(name, passed, data)
                return data

            info = await call("SageMath runtime health")
            record("SageMath version", bool(info.get("sage_version")), info.get("sage_version"))
            fraction = await call("Exact rational arithmetic", "1/3 + 1/6", expected="1/2")
            record("LaTeX result", fraction.get("latex") == r"\frac{1}{2}")
            await call("Sage exponent syntax", "2^10", expected="1024")
            await call("Polynomial generator and factorization", "R.<x> = QQ[]\nf = x^4 - 1\nf.factor()", expected="(x - 1) * (x + 1) * (x^2 + 1)")
            await call("Exact linear system", "M = matrix(QQ, [[2,1],[1,-1]])\nM.solve_right(vector(QQ,[5,1]))", expected="(2, 1)")
            await call("Finite field inverse", "GF(7)(3)^(-1)", expected="5")
            await call("Symbolic integration", "integral(sin(x), x, 0, pi)", expected="2")
            await call("Integer factorization", "factor(2^64-1)", expected="3 * 5 * 17 * 257 * 641 * 65537 * 6700417")
            output = await call("Printed and native output", "import os, sys\nprint('hello Sage')\nos.write(1, b'native stdout\\n')\nprint('diagnostic', file=sys.stderr)\n6*7", expected="42")
            record("Output capture preserves MCP framing", "hello Sage\n" in output.get("stdout", "") and "native stdout\n" in output.get("stdout", "") and "diagnostic\n" in output.get("stderr", ""))
            no_latex = await call("Optional LaTeX disabled", "1/2", expected="1/2", include_latex=False)
            record("LaTeX absent when disabled", "latex" not in no_latex)
            await call("Division error", "1/0", error="ZeroDivisionError")
            await call("Recovery after division error", "6*7", expected="42")
            await call("Syntax error", "for :", error="SyntaxError")
            await call("Recovery after syntax error", "6*7", expected="42")
            await call("State setup", "private_test_variable = 987")
            await call("Fresh state per call", "private_test_variable", error="NameError")
            await call("Statement-only script", "a = 5\nprint(a)")
            before = time.monotonic()
            await call("Infinite loop timeout", "while True: pass", error="TimeoutError", timeout_seconds=3)
            record("Timeout returns promptly", time.monotonic() - before < 9)
            await call("Recovery after timeout", "6*7", expected="42")
            capped = await call("Large stdout bounded", "print('z'*100000)\n42", expected="42")
            record("Output cap and truncation marker", capped.get("stdout_truncated") is True and len(capped.get("stdout", "").encode()) <= 80_000)
            result_cap = await call("Large result bounded", "'z'*30000", include_latex=False)
            record("Result cap and truncation marker", result_cap.get("result_truncated") is True and len(result_cap.get("result", "")) == 20_000)
            for name, args in [
                ("Empty code rejected", {"code": ""}),
                ("Oversized code rejected", {"code": "x" * 65_537}),
                ("Too short timeout rejected", {"code": "1", "timeout_seconds": 0}),
                ("Excessive timeout rejected", {"code": "1", "timeout_seconds": 121}),
                ("Missing code rejected", {}),
            ]:
                response = await session.call_tool("sage_execute", args)
                record(name, response.isError)
            response = await session.call_tool("not_a_tool", {})
            record("Unknown tool rejected", response.isError)
            await call("Recovery after invalid requests", "6*7", expected="42")

    report = {
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "launcher": str(launcher), "transport": "MCP stdio",
        "passed": sum(r["passed"] for r in records), "total": len(records),
        "all_passed": all(r["passed"] for r in records), "checks": records,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['passed']}/{report['total']} checks passed; report: {report_path}", flush=True)
    return report["all_passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--launcher", type=Path, default=Path(__file__).parent / "launch.sh")
    parser.add_argument("--report", type=Path, default=Path(__file__).parent / "test-report.json")
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.launcher.resolve(), args.report.resolve())) else 1)
