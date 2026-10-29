# Public release readiness

Review date: 2026-10-29. Baseline: `3b87818` (one imported snapshot commit).
Repository visibility must stay private until the owner reviews the changes and the open items below.

## Changes prepared

- Replaced machine-specific installation notes with a standalone README covering purpose, setup, tools, limitations, verification, and provenance.
- Made the launcher use a repository-local virtual environment and Sage on PATH, with explicit environment overrides and a helpful missing-Python error.
- Fixed the integration client to forward those overrides to its child server.
- Added repeatable tests of the MCP interface and process safeguards without requiring a Sage installation.
- Ignored generated integration reports, which can contain local paths and request contents.

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
| Real Sage integration suite (`test_mcp.py`) | Not run: SageMath unavailable in this execution environment |

The restricted execution sandbox initially allowed 9 of the 10 tests but caused MCP initialization to time out. The unchanged suite passed outside that sandbox. The tests use a controlled fake Sage executable and temporary files; they verify transport and orchestration, not Sage mathematics or preparser behavior. Python versions other than 3.14 were not tested in this review.

The tests cover missing/broken runtime errors, malformed/oversized/missing worker results, stdout and stderr limits, recovery, timeouts, process-group cleanup, cancellation, filtered environment variables, worker string truncation, MCP discovery/annotations, and source/timeout argument validation. They are not a sandbox certification or an exhaustive security audit.

## Privacy and provenance review

All tracked source and documentation and all nine blobs reachable from the original repository history were inspected. A targeted credential-pattern scan found no credential-like matches. No vendored third-party code, binary artifacts, raw conversations, personal documents, or license notices were present in the snapshot. Absence of matches does not establish that every possible secret or ownership issue has been excluded.

The original `README.source.md` and `launch.sh` contain personal absolute filesystem paths. Those paths are removed from the proposed tree, but remain visible in baseline commit `3b87818`. No history was rewritten. The owner must decide whether those historical paths are acceptable for public release or arrange an explicitly authorized history cleanup before changing visibility.

The snapshot records that the project arose from AI-assisted work, but omits original development history. That evidence does not establish ownership or third-party provenance. No license was added. A possible owner-selected license for the adapter code is MIT, contingent on confirming rights to all included code and any necessary notices. This proposal does not apply a license or change dependency licensing.

## Release checklist

- [x] Portable source-only installation instructions and launcher.
- [x] Explicit arbitrary-code-execution and not-a-sandbox warning.
- [x] Retain destructive/open-world MCP annotations for execution.
- [x] Isolated dependency install and process/protocol tests.
- [x] Review current files and imported history for privacy and provenance signals.
- [ ] Owner confirms provenance/rights and chooses an appropriate license and notices.
- [ ] Owner accepts historical personal paths or separately authorizes their removal from history.
- [ ] Run `test_mcp.py` against an actual supported Sage installation and inspect every result.
- [ ] Verify the desired deployment platform and supported Python versions.
- [ ] Parent/owner reviews draft PR and explicitly authorizes public visibility.

No visibility change, release publication, merge, force-push, installed-plugin edit, or Sage/system installation is part of this change.
