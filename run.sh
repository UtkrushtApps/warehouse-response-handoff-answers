#!/usr/bin/env bash
set -euo pipefail

cd /root/task
pip install -q -r requirements.txt

echo "Checking warehouse agent package..."
python -m compileall -q agent
python -m agent fixtures/example.json

echo "Readiness check passed. The package imports and fixture schema are valid."
