#!/usr/bin/env bash
set -euo pipefail
plugin_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
runtime_python="${SAGEMATH_MCP_PYTHON:-$plugin_dir/.venv/bin/python}"
if [[ ! -x "$runtime_python" ]]; then
    printf '%s\n' 'MCP Python not found. Create .venv beside launch.sh or set SAGEMATH_MCP_PYTHON to an executable path.' >&2
    exit 1
fi
export SAGE_EXECUTABLE="${SAGE_EXECUTABLE:-sage}"
exec "$runtime_python" "$plugin_dir/server.py"
