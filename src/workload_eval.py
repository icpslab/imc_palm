"""
Synthetic workload generator for the OFFLINE schedulability evaluation
(paper Section 4.1 / Section 4.2, Figures 3 and 4).

Generates NUM_TESTS_EVAL task sets per (m, target) combination, plus an
additional set varying the HC-task probability P_H at a fixed utilization.
Task sets are NOT filtered for schedulability here -- the acceptance ratio
itself is the metric of interest.

Output: RESULT_DIR/data/tasks_m_{m}_target_{t}.json
        RESULT_DIR/data/tasks_m_{m}_ph_{p}.json
"""

import os
import json
import random
import math

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from config import DATA_DIR, M_VALUES, TARGETS, P_H_VALUES, NUM_TESTS_EVAL


# ============================================================
# Multiprocessor workload generation
# ============================================================
def generate_multiprocessor_workload(m, target_util_per_core, p_h=0.5):
    target_util = m * target_util_per_core

    while True:
        n = random.randint(4 * m, 6 * m)
        tasks = []
        u_lo_sum = 0.0
        u_hi_sum = 0.0

        for _ in range(n):
            is_hc = random.random() < p_h
            u_base = random.uniform(0.05, 0.3)

            if is_hc:
                u_hi_raw = u_base
                u_lo_raw = u_hi_raw / random.uniform(1.0, 3.0)
            else:
                u_lo_raw = u_base
                u_hi_raw = random.uniform(0.001, u_lo_raw / 2.0)

            # Period drawn log-uniformly from [10, 500].
            period = round(math.exp(random.uniform(math.log(10), math.log(500))))

            tasks.append({
                "crit": "HC" if is_hc else "LC",
                "u_LO": u_lo_raw,
                "u_HI": u_hi_raw,
                "period": period
            })
            u_lo_sum += u_lo_raw
            u_hi_sum += u_hi_raw

        sys_max = max(u_lo_sum, u_hi_sum)
        scale_factor = target_util / sys_max

        valid = True
        for t in tasks:
            t["u_LO"] *= scale_factor
            t["u_HI"] *= scale_factor

            if t["u_LO"] > 0.85 or t["u_HI"] > 0.85:
                valid = False
                break

        if valid:
            return tasks


def main():
    num_tests = NUM_TESTS_EVAL
    save_dir = DATA_DIR
    os.makedirs(save_dir, exist_ok=True)

    # ============================================================
    # 1. Utilization variation (P_H = 0.5 fixed)
    # ============================================================
    for m in M_VALUES:
        print(f"\n>>> [Util variation] m={m} (tests={num_tests} per target)")
        for target in TARGETS:
            tasks_for_target = []
            for _ in range(num_tests):
                tasks_for_target.append(
                    generate_multiprocessor_workload(m, target, p_h=0.5))

            file_path = os.path.join(save_dir, f"tasks_m_{m}_target_{target:.2f}.json")
            with open(file_path, 'w') as f:
                json.dump(tasks_for_target, f)
            print(f"  Saved: {file_path}")

    # ============================================================
    # 2. P_H variation (target utilization = 0.80 fixed)
    # ============================================================
    fixed_target = 0.80

    for m in M_VALUES:
        print(f"\n>>> [P_H variation] m={m}, target={fixed_target} "
              f"(tests={num_tests} per P_H)")
        for p_h in P_H_VALUES:
            tasks_for_ph = []
            for _ in range(num_tests):
                tasks_for_ph.append(
                    generate_multiprocessor_workload(m, fixed_target, p_h=p_h))

            file_path = os.path.join(save_dir, f"tasks_m_{m}_ph_{p_h:.1f}.json")
            with open(file_path, 'w') as f:
                json.dump(tasks_for_ph, f)
            print(f"  Saved: {file_path}")

    print("\nAll generation complete.")


if __name__ == "__main__":
    main()
