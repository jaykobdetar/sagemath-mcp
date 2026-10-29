#!/usr/bin/env bash
set -euo pipefail
plugin_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
runtime_python="${SAGEMATH_MCP_PYTHON:-/home/jaykob/Documents/Codex/Integrations/sagemath-mcp/venv/bin/python}"
export SAGE_EXECUTABLE="${SAGE_EXECUTABLE:-/home/jaykob/miniforge3/envs/sage/bin/sage}"
exec "$runtime_python" "$plugin_dir/server.py"
