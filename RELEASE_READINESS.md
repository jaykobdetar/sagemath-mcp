# Public release readiness

Review date: 2026-10-29. Baseline: `3b87818` (one imported snapshot commit).
Repository visibility must stay private until the owner reviews the changes and the open items below.

## Changes prepared

- Replaced machine-specific installation notes with a standalone README covering purpose, setup, tools, limitations, verification, and provenance.
- Made the launcher use a repository-local virtual environment and Sage on PATH, with explicit environment overrides and a helpful missing-Python error.
- Fixed the integration client to forward those overrides to its child server.
- Added repeatable tests of the MCP interface and process safeguards without requiring a Sage installation.
- Ignored generated integration reports, which can contain local paths and request contents.
- Added the MIT license with explicit owner authorization, retaining dependency licensing boundaries.

## Verification evidence

Executed on Linux with Python 3.14.7 in an isolated virtual environment:

| Check | Result |
| --- | --- |
| Install `requirements.lock` from official PyPI | Passed; all pins resolved |
| `.venv/bin/python -m pip check` | Passed; no broken requirements |
| `.venv/bin/python -m unittest discover -s tests -v` | 10 tests passed in 1.266 seconds outside the execution sandbox |
| `bash -n launch.sh` | Passed |
| Python compilation of server, worker, integration client, and tests | Passed |
| `git diff --check` | Passed |
| Real Sage integration suite (`test_mcp.py`) | 38/38 checks passed against existing SageMath 10.7 on Linux |

A follow-up on 2026-10-29 located an existing SageMath 10.7 executable in a standard local Conda environment (it was absent from PATH). The reviewed checkout's integration suite completed at 20:19:00 UTC with 38/38 checks passing. Execution used a 4 GiB per-process address-space limit, a 90-second per-process CPU limit, and a 180-second suite wall-time limit; calculation workers also retained their own request timeouts and single-thread settings. No Sage installation or environment modification was performed. The ignored local report `test-report-real-sage.json` contains full details and local paths; it is deliberately not committed.

The restricted execution sandbox initially allowed 9 of the 10 tests but caused MCP initialization to time out. The unchanged suite passed outside that sandbox. The tests use a controlled fake Sage executable and temporary files; they verify transport and orchestration, not Sage mathematics or preparser behavior. Python versions other than 3.14 were not tested in this review.

The tests cover missing/broken runtime errors, malformed/oversized/missing worker results, stdout and stderr limits, recovery, timeouts, process-group cleanup, cancellation, filtered environment variables, worker string truncation, MCP discovery/annotations, and source/timeout argument validation. They are not a sandbox certification or an exhaustive security audit.

## Privacy and provenance review

All tracked source and documentation and all nine blobs reachable from the original repository history were inspected. A targeted credential-pattern scan found no credential-like matches. No vendored third-party code, binary artifacts, raw conversations, personal documents, or license notices were present in the snapshot. Absence of matches does not establish that every possible secret or ownership issue has been excluded.

The original `README.source.md` and `launch.sh` contain personal absolute filesystem paths. Those paths are removed from the proposed tree, but remain visible in baseline commit `3b87818`. No history was rewritten. The owner must decide whether those historical paths are acceptable for public release or arrange an explicitly authorized history cleanup before changing visibility.

The snapshot records that the project arose from AI-assisted work, but omits original development history. On 2026-10-29, in response to the provenance and license question, the repository owner stated that all of the code was created by AI and explicitly authorized MIT licensing. The repository now includes the MIT license. This records the owner's assertion and authorization, not an independent legal determination of copyright ownership or third-party provenance. No existing third-party notices were removed; dependencies retain their own licenses.

## Release checklist

- [x] Portable source-only installation instructions and launcher.
- [x] Explicit arbitrary-code-execution and not-a-sandbox warning.
- [x] Retain destructive/open-world MCP annotations for execution.
- [x] Isolated dependency install and process/protocol tests.
- [x] Review current files and imported history for privacy and provenance signals.
- [x] Record owner's AI-origin assertion and explicit MIT authorization; add LICENSE and consistent README metadata.
- [ ] Owner accepts historical personal paths or separately authorizes their removal from history.
- [x] Run `test_mcp.py` against existing SageMath 10.7 and inspect every result: 38/38 passed.
- [ ] Verify the desired deployment platform and supported Python versions.
- [ ] Parent/owner reviews draft PR and explicitly authorizes public visibility.

No visibility change, release publication, merge, force-push, installed-plugin edit, or Sage/system installation is part of this change.
