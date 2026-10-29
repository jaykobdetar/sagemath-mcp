# SageMath MCP

A small local MCP server that exposes an existing SageMath installation to an agent.

## What is preserved

Provides Sage runtime information and bounded expression/script execution through stdio MCP.

This is a private, source-only preservation snapshot of the user-selected local project **P0456**, prepared on 2026-10-29. The user described these projects as arising from AI-assisted work. This note records archival provenance, not a claim about authorship or scientific validity. The original Git history was not imported.

## Setup and dependencies

Python 3.11+ plus a separate working SageMath installation. Install requirements.txt in an isolated Python environment.

## Entry points

server.py is the MCP entrypoint; launch.sh starts the configured runtime. Use SAGE_EXECUTABLE and SAGEMATH_MCP_PYTHON overrides; inspect the launcher defaults before running on another machine.

## Status and limitations

The original notes contain machine-specific paths. This is not a security sandbox. Sage itself and installed plugin configuration are not included.

No project code, installation steps or tests were executed during preservation. Existing README/source claims have not been independently revalidated. For the original project documentation, see [README.source.md](README.source.md).

## Backup scope

Only the reviewed text source, tests, selected manifests/configurations and technical documentation are included. Credentials, .env/auth configuration, raw conversations, personal documents, live state, model weights, dependencies, generated datasets and bulky outputs were excluded. Local originals remain in place until separately approved and safe to remove. A successful source backup alone is not proof that all runtime data or experiment evidence has been preserved.
