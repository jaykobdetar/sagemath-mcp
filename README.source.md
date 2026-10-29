# SageMath MCP

A local Codex plugin exposing your existing SageMath installation over MCP stdio.
No account, API key, cloud service, or always-running server is required.

## Tools

- `sage_info()` checks that SageMath starts and reports its version and limits.
- `sage_execute(code, timeout_seconds=30, include_latex=True)` runs a Sage expression
  or multiline script and returns result text, Sage type, optional LaTeX, captured
  stdout/stderr, elapsed time, and structured errors.

The namespace includes `sage.all` and symbolic `x`. Sage's preparser supports
exact fractions, `^` for exponentiation, and polynomial generator declarations.
The last expression is returned; `print()` output is also captured.

```sage
R.<t> = QQ[]
f = t^4 - 1
f.factor()
```

Expected result: `(t - 1) * (t + 1) * (t^2 + 1)`.

```sage
M = matrix(QQ, [[2, 1], [1, -1]])
M.solve_right(vector(QQ, [5, 1]))
```

Expected result: `(2, 1)`.

## Installed runtime

- Sage executable: `/home/jaykob/miniforge3/envs/sage/bin/sage` (SageMath 10.7).
- MCP Python: `/home/jaykob/Documents/Codex/Integrations/sagemath-mcp/venv/bin/python`.
- Personal plugin source: `/home/jaykob/plugins/sagemath-mcp`.
- Marketplace: `/home/jaykob/.agents/plugins/marketplace.json`.
- Codex installation: `sagemath-mcp@personal`.

Start a new Codex task after installation to pick up the tools. Try:
"Use SageMath to factor x^4 - 1 and integrate sin(x) from 0 to pi."

`launch.sh` supports `SAGE_EXECUTABLE` and `SAGEMATH_MCP_PYTHON` environment overrides.
The MCP command uses the absolute personal-source launcher path, so it works
without plugin-path environment substitution. The configured runtime paths are
specific to this computer. For another machine, update that path in `.mcp.json`,
install SageMath and a Python 3.11+ virtual environment with
`python -m pip install -r requirements.lock`, then set these overrides in the MCP
configuration or update the launcher's defaults. The plugin is not an installer
for SageMath itself.

## Execution behavior

Every request gets a fresh process and temporary working directory. Variables
and relative-path files disappear after the request. Save desired artifacts to
an explicit absolute path. Code has normal local Python permissions, including
filesystem and network access; process isolation is not a security sandbox.
The server does not send calculations to an external service.

The default wall-clock limit is 30 seconds, including startup, with a maximum of
120 seconds. At most two workers run at once. Code is limited to 65,536 characters.
Each output stream retains up to 80,000 bytes; result and LaTeX strings retain up
to 20,000 characters each, with explicit truncation flags. Sage subprocess groups
are terminated after completion, timeout, or request cancellation. This bounds
returned output and runtime, not arbitrary code's memory or filesystem use.

## Verification

`test_mcp.py` uses the official MCP client to initialize the server, discover tools,
and check real calculations, Sage syntax, errors, fresh state, timeouts, output
limits, and recovery. To test a specific installed package:

```bash
/home/jaykob/Documents/Codex/Integrations/sagemath-mcp/venv/bin/python \
  test_mcp.py --launcher /home/jaykob/plugins/sagemath-mcp/launch.sh \
  --report test-report.json
```

The SDK is pinned to the tested 1.x FastMCP API; `requirements.lock` records all
installed dependency versions. Codex caches plugin metadata; reinstall after
changing the manifest or MCP configuration. Its MCP command launches the personal
source directory. Remove it using `codex plugin remove sagemath-mcp@personal`.

## References

- [Sage preparser](https://doc.sagemath.org/html/en/reference/repl/sage/repl/preparse.html)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Codex plugin development](https://learn.chatgpt.com/docs/build-plugins)
