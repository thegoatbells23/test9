#!/bin/bash
# Replace the counties collection in the local MongoDB with the counties
# in a tab-separated file, renamed to our field names (see counties/load.py).
# Load the states first (bin/load_states.sh): a county's state should exist.
#
# Usage: bin/load_counties.sh [FILE]     (default: counties/raw_data/county_pops2.csv)
set -euo pipefail

cd "$(dirname "$0")/.."
set +u
source geodata2026-venv/bin/activate
set -u
export PYTHONPATH=$PWD

python counties/load.py "${1:-counties/raw_data/county_pops2.csv}"
