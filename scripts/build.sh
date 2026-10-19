#!/bin/sh
# scripts/build.py, which does the work on every system (python3 scripts/build.py --help).
exec python3 "$(dirname "$0")/build.py" "$@"
