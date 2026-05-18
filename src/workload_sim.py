"""
Schedulable workload generator for the RUNTIME survivability simulation
(paper Section 4.1 / Section 4.3, Figures 5, 6 and 7).

Unlike workload_eval.py, every task set produced here is guaranteed to be
partitionable under the tightened EDF-VD-IMC test (Theorem 1) with FFD, so
that the runtime simulator always has a valid initial assignment. Integer
execution budgets (c_LO, c_HI) are injected and utilizations are re-derived
from them to remove model/simulator rounding mismatch.

Output: RESULT_DIR/data/stasks_m_{m}_target_{t}.json
"""

import os
import json
import random
import copy
import math

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from config import DATA_DIR, M_VALUES, TARGETS, NUM_VALID_SIM


# ============================================================
# 1. Tightened EDF-VD-IMC schedulability test (Theorem 1)
# ============================================================
def compute_x_max(U_LC_A: float, U_LC_D: float, U_HC_H: float):
    denom = U_LC_A - U_LC_D
    if denom <= 0.0:
        if U_HC_H + U_LC_D <= 1.0:
            return 1.0
        return None
    numer = 1.0 - U_HC_H - U_LC_D
    if numer <= 0.0:
        return None
    x_max = numer / denom
    if x_max > 1.0:
        x_max = 1.0
    return x_max


def is_schedulable_new(U_LC_A, U_HC_L, U_LC_D, U_HC_H, hc_tasks, lc_tasks):
    """Theorem 1: U_A_L + sum(min(u_L/x, u_H)) <= 1, with x = x*."""
    x = compute_x_max(U_LC_A, U_LC_D, U_HC_H)
    if x is None:
        return False
    lo_sum = U_LC_A
    for (u_l, u_h) in hc_tasks:
        if u_l / x >= u_h:
            lo_sum += u_h
        else:
            lo_sum += u_l / x
    return lo_sum <= 1.0


class Processor:
    def __init__(self, proc_id, sched_func):
        self.id = proc_id
        self._sched_func = sched_func
        self.U_LC_A = 0.0
        self.U_HC_L = 0.0
        self.U_LC_D = 0.0
        self.U_HC_H = 0.0
        self.hc_tasks = []
        self.lc_tasks = []
        self.tasks = []

    def try_add(self, task: dict) -> bool:
        if task["crit"] == "HC":
            new_U_LC_A, new_U_LC_D = self.U_LC_A, self.U_LC_D
            new_U_HC_L = self.U_HC_L + task["u_LO"]
            new_U_HC_H = self.U_HC_H + task["u_HI"]
            new_hc = self.hc_tasks + [(task["u_LO"], task["u_HI"])]
            new_lc = self.lc_tasks
        else:
            new_U_LC_A = self.U_LC_A + task["u_LO"]
            new_U_LC_D = self.U_LC_D + task["u_HI"]
            new_U_HC_L, new_U_HC_H = self.U_HC_L, self.U_HC_H
            new_hc = self.hc_tasks
            new_lc = self.lc_tasks + [(task["u_LO"], task["u_HI"])]
        return self._sched_func(new_U_LC_A, new_U_HC_L, new_U_LC_D,
                                new_U_HC_H, new_hc, new_lc)

    def add(self, task: dict):
        if task["crit"] == "HC":
            self.U_HC_L += task["u_LO"]
            self.U_HC_H += task["u_HI"]
            self.hc_tasks.append((task["u_LO"], task["u_HI"]))
        else:
            self.U_LC_A += task["u_LO"]
            self.U_LC_D += task["u_HI"]
            self.lc_tasks.append((task["u_LO"], task["u_HI"]))
        self.tasks.append(task)


def partition_ffd_new(tasks, m):
    sorted_tasks = sorted(tasks, key=lambda t: max(t["u_LO"], t["u_HI"]),
                          reverse=True)
    procs = [Processor(i, is_schedulable_new) for i in range(m)]

    for task in sorted_tasks:
        placed = False
        for p in procs:
            if p.try_add(task):
                p.add(task)
                placed = True
                break
        if not placed:
            return None
    return procs


# ============================================================
# 2. Random multiprocessor workload
# ============================================================
def generate_multiprocessor_workload(m, target_util_per_core):
    target_util = m * target_util_per_core

    while True:
        n = random.randint(4 * m, 6 * m)
        tasks = []
        u_lo_sum = 0.0
        u_hi_sum = 0.0

        for _ in range(n):
            is_hc = random.random() < 0.5
            u_base = random.uniform(0.05, 0.3)

            if is_hc:
                u_hi_raw = u_base
                u_lo_raw = u_hi_raw / random.uniform(1.0, 3.0)
            else:
                u_lo_raw = u_base
                u_hi_raw = random.uniform(0.001, u_lo_raw / 2.0)

            tasks.append({"crit": "HC" if is_hc else "LC",
                          "u_LO": u_lo_raw, "u_HI": u_hi_raw})
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


# ============================================================
# 3. Generate only schedulable task sets
# ============================================================
def generate_valid_task_set(m, target):
    while True:
        raw_tasks = generate_multiprocessor_workload(m, target)

        for i, t in enumerate(raw_tasks):
            t["id"] = i
            # Period: log-uniform over [10, 500], rounded to integer.
            t["period"] = round(math.exp(random.uniform(math.log(10),
                                                        math.log(500))))
            # Integer execution budgets.
            t["c_LO"] = max(1, int(t["u_LO"] * t["period"]))
            t["c_HI"] = max(1, int(t["u_HI"] * t["period"]))
            # Re-derive utilizations from integer budgets.
            t["u_LO"] = t["c_LO"] / t["period"]
            t["u_HI"] = t["c_HI"] / t["period"]

        # deepcopy so the partition test does not pollute the task objects.
        procs = partition_ffd_new(copy.deepcopy(raw_tasks), m)

        if procs is not None:
            return raw_tasks


# ============================================================
# 4. Main
# ============================================================
def main():
    num_valid_tests = NUM_VALID_SIM
    save_dir = DATA_DIR
    os.makedirs(save_dir, exist_ok=True)

    for m in M_VALUES:
        print(f"\n>>> Task generation started for m={m} "
              f"(Targeting {num_valid_tests} valid sets per util)")
        for target in TARGETS:
            valid_tasks_for_target = []

            print(f"  - Finding valid sets for Target {target:.2f}...",
                  end="", flush=True)
            for i in range(num_valid_tests):
                valid_task_set = generate_valid_task_set(m, target)
                valid_tasks_for_target.append(valid_task_set)

                if (i + 1) % 10 == 0:
                    print(".", end="", flush=True)

            print(" Done!")

            file_path = os.path.join(
                save_dir, f"stasks_m_{m}_target_{target:.2f}.json")
            with open(file_path, 'w') as f:
                json.dump(valid_tasks_for_target, f, indent=2)

    print("\nAll strictly schedulable generation complete.")


if __name__ == "__main__":
    main()
