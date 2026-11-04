#!/usr/bin/env bash
# One-time setup of the GhoulGate engine environment. Run from anywhere.
set -e
cd "$(dirname "$0")"
uv venv -q .venv
uv pip install -q --python .venv/bin/python -r requirements.txt
uv pip install -q --python .venv/bin/python --no-deps tinysoundfont
echo "engine/.venv ready"
