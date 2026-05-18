# IMC-PALM

Simulation artifact for the paper:

> **IMC-PALM: Enhancing Survivability of Imprecise Mixed-Criticality
> Cyber-Physical Systems via Mode-Balanced Partitioning and Adaptive
> Task Migration**
> Jaewoo Lee, Dept. of Industrial Security, Chung-Ang University.
> in submission to Systems journal, 2026.

IMC-PALM is a two-phase framework for partitioned imprecise mixed-criticality
(IMC) multiprocessor systems. The **offline phase** combines a tightened
EDF-VD-IMC schedulability test (Theorem 1) with a Mode-Balanced Partitioning
(MBP) heuristic. The **runtime phase** migrates low-criticality (LC) tasks
from a mode-switched processor to neighboring processors that remain in LO
mode, and returns them to their home processor upon recovery.

This repository reproduces all simulation results and figures in Section 4 of
the paper.

## Repository layout

```
imc-palm/
├── config.py                       # Shared paths and experiment parameters
├── requirements.txt
├── src/
│   ├── workload_eval.py            # Workload generator for offline evaluation
│   ├── workload_sim.py             # Schedulable-only workload generator (sim)
│   ├── offline_schedulability.py   # Offline schedulability (Section 4.2)
│   ├── runtime_simulation.py       # Runtime survivability simulator (Sec 4.3)
│   ├── plot_schedulability.py      # Figures 3 and 4
│   └── plot_survivability.py       # Figures 5, 6 and 7
└── scripts/
    └── run_all.sh                  # End-to-end pipeline
```

## Code ↔ paper mapping

| Module | Paper section | Produces |
|---|---|---|
| `workload_eval.py` | Sec. 4.1 | `tasks_m_*_target_*.json`, `tasks_m_*_ph_*.json` (5000 sets each) |
| `workload_sim.py` | Sec. 4.1 | `stasks_m_*_target_*.json` (schedulable sets only) |
| `offline_schedulability.py` | Sec. 4.2 | `simulation_results.csv`, `simulation_ph_results.csv` |
| `runtime_simulation.py` | Sec. 4.3 | `imc_simulation_recovery_results.csv`, `imc_prob_recovery_results.csv`, `imc_overhead_recovery_results.csv` |
| `plot_schedulability.py` | Figs. 3–4 | `acceptance_ratio_util_m{m}.pdf`, `acceptance_ratio_ph_m{m}.pdf` |
| `plot_survivability.py` | Figs. 5–7 | `imc_simulation_m{m}.pdf`, `imc_prob_m{m}.pdf`, `imc_overhead_m{m}.pdf` |

### Compared algorithms (offline, Section 4.2)

| Label in paper | Partitioning | Schedulability test |
|---|---|---|
| `FFD(base)` | First-Fit Decreasing | Standard EDF-VD-IMC [7] |
| `IMC-PALM(v1)` | First-Fit Decreasing | Tightened test (Theorem 1) |
| `IMC-PALM(v2)` | Mode-Balanced Partitioning (Algorithm 1) | Tightened test (Theorem 1) |
| `CU-UDP` | Criticality-Unaware UDP [12] | Standard EDF-VD-IMC [7] |

### Compared configurations (runtime, Section 4.3)

| Label in paper | Migration | Home-processor recovery |
|---|---|---|
| `Migration OFF` | none (degrade immediately) | — |
| `Migration NoRec` | yes (Algorithm 2) | no |
| `Migration Rec` | yes (Algorithm 2) | yes (Algorithm 3) — full IMC-PALM |

## Requirements

- Python 3.8+
- `matplotlib`, `pandas` (for plotting only)

```bash
pip install -r requirements.txt
```

The schedulability and simulation logic depends only on the Python standard
library; the plotting scripts additionally require matplotlib and pandas.

## Usage

Run the full pipeline (generation → evaluation → plotting):

```bash
./scripts/run_all.sh
```

Or run each stage individually from the repository root:

```bash
python3 src/workload_eval.py          # generate offline workloads
python3 src/workload_sim.py           # generate schedulable workloads
python3 src/offline_schedulability.py # Section 4.2
python3 src/runtime_simulation.py     # Section 4.3
python3 src/plot_schedulability.py    # Figures 3, 4
python3 src/plot_survivability.py     # Figures 5, 6, 7
```

All artifacts are written to `./results/` by default. To use a different
output location:

```bash
export IMC_PALM_DATA=/path/to/output
```

## Reproducing the paper's numbers

The defaults in `config.py` match the paper:

- `NUM_TESTS_EVAL = 5000` task sets per point (offline, Section 4.2)
- `MAX_SIM_SETS = 1000` task sets per point (runtime, Section 4.3)
- `SIM_TICKS = 10000` simulation time units
- `m ∈ {2, 4, 8}`, `Ut ∈ {0.70, ..., 0.95}`, `P_H ∈ {0.1, ..., 0.9}`

Generating the full 5000-set workloads and running the 10,000-tick simulation
is computationally intensive. For a quick sanity check, reduce these values in
`config.py` (e.g. `NUM_TESTS_EVAL = 50`, `MAX_SIM_SETS = 20`,
`SIM_TICKS = 500`). The runtime simulator fixes the RNG seed per task set, so
results are deterministic for a given workload.

## Notes

- Periods are drawn log-uniformly from `[10, 500]`; per-task utilizations are
  scaled so the larger of the collective LO-/HI-mode utilizations equals the
  target `m · Ut`.
- For the runtime simulation, integer execution budgets are injected and
  utilizations are re-derived from them, removing rounding mismatch between the
  analytical model and the tick-driven simulator.
- The migration overhead model inflates a migrated task's active budget by a
  factor `(1 + α)`; the mandatory (degraded) budget is left unchanged.

## License

Released under the MIT License. See [LICENSE](LICENSE).
