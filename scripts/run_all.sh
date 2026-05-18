#!/usr/bin/env bash
#
# Reproduce all results and figures from the IMC-PALM paper.
#
# Usage:
#   ./scripts/run_all.sh
#
# Output goes to ./results (override with the IMC_PALM_DATA env var).

set -e

cd "$(dirname "$0")/.."

echo "=== [1/6] Generating workloads for offline evaluation ==="
python3 src/workload_eval.py

echo "=== [2/6] Generating schedulable workloads for runtime simulation ==="
python3 src/workload_sim.py

echo "=== [3/6] Offline schedulability evaluation (Section 4.2) ==="
python3 src/offline_schedulability.py

echo "=== [4/6] Runtime survivability simulation (Section 4.3) ==="
python3 src/runtime_simulation.py

echo "=== [5/6] Plotting offline schedulability (Figs 3, 4) ==="
python3 src/plot_schedulability.py

echo "=== [6/6] Plotting runtime survivability (Figs 5, 6, 7) ==="
python3 src/plot_survivability.py

echo "=== Done. See the results/ directory. ==="
