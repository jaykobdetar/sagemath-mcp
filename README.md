# SageMath MCP

A local stdio [Model Context Protocol](https://modelcontextprotocol.io/) server for an existing [SageMath](https://www.sagemath.org/) installation. It exposes exact arithmetic, algebra, calculus, matrices, and Sage scripts to an MCP client. No account, API key, cloud service, or background HTTP server is required.

## Status

This is a small experimental source distribution, not an official SageMath or MCP project. The MCP protocol and process safeguards have automated tests that do not require Sage. The separate real-Sage suite passed all 38 checks against an existing SageMath 10.7 installation on Linux; other Sage versions and platforms remain unverified. See [RELEASE_READINESS.md](RELEASE_READINESS.md) for evidence and outstanding decisions.

## Setup

Requirements: Linux or another POSIX system with Bash, Python 3.11+, and a separately installed, working SageMath executable. Windows process management is not supported. Install Sage using the [official installation guide](https://doc.sagemath.org/html/en/installation/); this repository does not install or bundle Sage.

From a checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
export SAGE_EXECUTABLE=/absolute/path/to/sage
./launch.sh
```

The server waits for an MCP client on stdin; it is not an interactive terminal. `launch.sh` uses `.venv/bin/python` beside itself and finds `sage` on PATH unless overridden. Set `SAGEMATH_MCP_PYTHON` to an absolute executable path to use another environment. Paths containing spaces are supported.

Configure a stdio MCP client using its documented configuration mechanism. For clients using the `mcpServers` convention, this is an example (replace both paths):

```json
{
  "mcpServers": {
    "sagemath": {
      "command": "/absolute/path/to/sagemath-mcp/launch.sh",
      "env": {"SAGE_EXECUTABLE": "/absolute/path/to/sage"}
    }
  }
}
```

No Codex plugin manifest is included; use the client's direct MCP server configuration. Keep local client configuration out of Git.

## Tools and examples

- `sage_info()` starts Sage and reports its version and supported limits.
- `sage_execute(code, timeout_seconds=30, include_latex=True)` returns the last expression, its Sage type, optional LaTeX, captured stdout/stderr, elapsed time, and structured errors.

Each call imports `sage.all`, defines symbolic `x`, and preparses Sage syntax such as exact fractions, `^`, and polynomial generator declarations:

```sage
R.<t> = QQ[]
f = t^4 - 1
f.factor()
```

Expected result: `(t - 1) * (t + 1) * (t^2 + 1)`. Expressions such as `1/3 + 1/6` should return `1/2`. Statements and `print()` are supported too.

## Execution and trust boundary

**This executes arbitrary local code and is not a security sandbox.** Only run code you trust. Calculations have the server user's filesystem and network permissions, can read local credentials, and can modify or delete files. Filtering inherited environment variables does not prevent filesystem access. Do not expose this server to untrusted users or run it with elevated privileges.

Each request uses a fresh process, namespace, and temporary working directory. Variables and ordinary relative-path files do not persist. An explicit absolute path can save artifacts outside that directory. The server itself does not send calculations to an external service, but submitted code can access the network.

The default worker timeout is 30 seconds including Sage startup, maximum 120 seconds. At most two workers run concurrently; queue time is additional. Code is limited to 65,536 characters. Each stream retains an 80,000-byte prefix; result and LaTeX strings retain 20,000 characters each, with truncation flags. Worker JSON is limited to 1,000,000 bytes. These limits bound returned data, not memory, disk use, or the work needed to format a result. Process groups are killed on completion, timeout, and cancellation; deliberately detached descendants can escape that cleanup. Use external OS isolation for stronger resource controls.

## Tests

```bash
# Protocol, validation, launcher, and process tests using a controlled fake worker:
.venv/bin/python -m unittest discover -s tests -v

# Real Sage integration (requires a separately installed Sage):
export SAGE_EXECUTABLE=/absolute/path/to/sage
.venv/bin/python test_mcp.py --report test-report.json
```

The integration suite checks real calculations, Sage syntax, fresh state, errors, timeouts, output limits, and recovery. Test reports may contain local executable paths and submitted code; they are ignored by Git. `requirements.txt` lists direct dependencies; `requirements.lock` pins the complete dependency set used for verification.

## Provenance and licensing

The initial commit preserves a selected local project snapshot imported on 2026-10-29. The project was described as AI-assisted; its original Git history and installed plugin configuration were not imported. The prior machine-specific setup notes were replaced by this portable guide. No broader authorship or ownership conclusion can be drawn from this snapshot.

Licensed under the [MIT License](LICENSE) (SPDX: `MIT`). On 2026-10-29, the repository owner stated that all of the code was created by AI and explicitly authorized MIT licensing. This records the owner's assertion and choice; it is not an independent determination of copyright ownership or third-party provenance. Dependencies retain their own licenses; they are not bundled in this repository.
