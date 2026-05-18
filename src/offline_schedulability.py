"""
Offline schedulability evaluation (paper Section 4.2, Figures 3 and 4).

Compares four partitioning algorithms over the workloads produced by
workload_eval.py:

    FFD(base)      - FFD + standard EDF-VD-IMC test         [7]
    IMC-PALM(v1)   - FFD + tightened Theorem 1 test
    IMC-PALM(v2)   - Mode-Balanced Partitioning + Theorem 1 test
    CU-UDP         - Criticality-Unaware UDP + standard test [12]

(The internal function names below retain their original short names;
the CSV columns use the paper's algorithm labels.)

Outputs:
    RESULT_DIR/simulation_results.csv      (utilization variation)
    RESULT_DIR/simulation_ph_results.csv   (P_H variation)
"""

import os
import json
import csv

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from config import DATA_DIR, RESULT_DIR, M_VALUES, TARGETS, P_H_VALUES


# ============================================================
# Schedulability formulas and processor class
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


def is_schedulable_original(U_LC_A, U_HC_L, U_LC_D, U_HC_H, hc_tasks, lc_tasks):
    """Standard EDF-VD-IMC test [7]: U_A_L + U_L_H / x <= 1."""
    x = compute_x_max(U_LC_A, U_LC_D, U_HC_H)
    if x is None:
        return False
    lo_util = (U_HC_L / x) + U_LC_A
    return lo_util <= 1.0


def is_schedulable_new(U_LC_A, U_HC_L, U_LC_D, U_HC_H, hc_tasks, lc_tasks):
    """Tightened test (Theorem 1): U_A_L + sum(min(u_L/x, u_H)) <= 1."""
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
    def __init__(self, sched_func):
        self.U_LC_A = 0.0
        self.U_HC_L = 0.0
        self.U_LC_D = 0.0
        self.U_HC_H = 0.0
        self.hc_tasks = []
        self.lc_tasks = []
        self.tasks = []
        self._sched_func = sched_func

    @property
    def U_LO(self) -> float:
        return self.U_LC_A + self.U_HC_L

    @property
    def U_HI(self) -> float:
        return self.U_LC_D + self.U_HC_H

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


# ============================================================
# Partitioning algorithms
# ============================================================
def partition_ffd_original(tasks, m):
    """FFD(base): FFD + standard EDF-VD-IMC test."""
    sorted_tasks = sorted(tasks, key=lambda t: max(t["u_LO"], t["u_HI"]),
                          reverse=True)
    procs = [Processor(is_schedulable_original) for _ in range(m)]
    for task in sorted_tasks:
        if not any(p.try_add(task) and not p.add(task) for p in procs):
            return False
    return True


def partition_ffd_new(tasks, m):
    """IMC-PALM(v1): FFD + tightened Theorem 1 test."""
    sorted_tasks = sorted(tasks, key=lambda t: max(t["u_LO"], t["u_HI"]),
                          reverse=True)
    procs = [Processor(is_schedulable_new) for _ in range(m)]
    for task in sorted_tasks:
        if not any(p.try_add(task) and not p.add(task) for p in procs):
            return False
    return True


def partition_mb_new(tasks, m):
    """IMC-PALM(v2): Mode-Balanced Partitioning + Theorem 1 test (Algorithm 1)."""
    sorted_tasks = sorted(tasks, key=lambda t: max(t["u_LO"], t["u_HI"]),
                          reverse=True)
    procs = [Processor(is_schedulable_new) for _ in range(m)]
    for task in sorted_tasks:
        sorted_procs = sorted(
            procs,
            key=lambda p: p.U_HI - p.U_LO if task["crit"] == "HC"
            else p.U_LO - p.U_HI)
        if not any(p.try_add(task) and not p.add(task) for p in sorted_procs):
            return False
    return True


def partition_cu_udp_original(tasks, m):
    """CU-UDP: Criticality-Unaware UDP + standard EDF-VD-IMC test [12]."""
    sorted_tasks = sorted(
        tasks,
        key=lambda t: t["u_HI"] if t["crit"] == "HC" else t["u_LO"],
        reverse=True)
    procs = [Processor(is_schedulable_original) for _ in range(m)]
    for task in sorted_tasks:
        sorted_procs = (sorted(procs, key=lambda p: p.U_HC_H - p.U_HC_L)
                        if task["crit"] == "HC" else procs)
        if not any(p.try_add(task) and not p.add(task) for p in sorted_procs):
            return False
    return True


# ============================================================
# Single-dataset evaluation
# ============================================================
def evaluate_dataset(all_tasks, m):
    num_tests = len(all_tasks)
    acc_orig = sum(1 for tasks in all_tasks if partition_ffd_original(tasks, m))
    acc_ffd_new = sum(1 for tasks in all_tasks if partition_ffd_new(tasks, m))
    acc_mb_new = sum(1 for tasks in all_tasks if partition_mb_new(tasks, m))
    acc_cu_udp_orig = sum(1 for tasks in all_tasks
                          if partition_cu_udp_original(tasks, m))

    r_orig = (acc_orig / num_tests) * 100
    r_ffd_new = (acc_ffd_new / num_tests) * 100
    r_mb_new = (acc_mb_new / num_tests) * 100
    r_cu_udp_orig = (acc_cu_udp_orig / num_tests) * 100

    return r_orig, r_ffd_new, r_mb_new, r_cu_udp_orig


# ============================================================
# Main: evaluate and save
# ============================================================
def main():
    data_dir = DATA_DIR
    result_dir = RESULT_DIR
    os.makedirs(result_dir, exist_ok=True)

    # --------------------------------------------------------
    # 1. Utilization variation (P_H = 0.5 fixed)  -> Figure 3
    # --------------------------------------------------------
    csv_file_path = os.path.join(result_dir, "simulation_results.csv")

    with open(csv_file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["m", "Target", "FFD_base", "IMC_PALM_v1",
                         "IMC_PALM_v2", "CU_UDP"])

        for m in M_VALUES:
            print(f"\n>>> [Util variation] Evaluating for m={m}")
            for target in TARGETS:
                file_path = os.path.join(
                    data_dir, f"tasks_m_{m}_target_{target:.2f}.json")
                if not os.path.exists(file_path):
                    print(f"  Data missing: {file_path}")
                    continue

                with open(file_path, 'r') as jf:
                    all_tasks = json.load(jf)

                r_orig, r_ffd_new, r_mb_new, r_cu_udp_orig = \
                    evaluate_dataset(all_tasks, m)
                writer.writerow([m, target, r_orig, r_ffd_new,
                                 r_mb_new, r_cu_udp_orig])
                print(f"  Target {target:.2f} done.")

    print(f"\nUtil variation saved to: {csv_file_path}")

    # --------------------------------------------------------
    # 2. P_H variation (target utilization = 0.80 fixed) -> Figure 4
    # --------------------------------------------------------
    csv_ph_path = os.path.join(result_dir, "simulation_ph_results.csv")

    with open(csv_ph_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["m", "P_H", "FFD_base", "IMC_PALM_v1",
                         "IMC_PALM_v2", "CU_UDP"])

        for m in M_VALUES:
            print(f"\n>>> [P_H variation] Evaluating for m={m}")
            for p_h in P_H_VALUES:
                file_path = os.path.join(
                    data_dir, f"tasks_m_{m}_ph_{p_h:.1f}.json")
                if not os.path.exists(file_path):
                    print(f"  Data missing: {file_path}")
                    continue

                with open(file_path, 'r') as jf:
                    all_tasks = json.load(jf)

                r_orig, r_ffd_new, r_mb_new, r_cu_udp_orig = \
                    evaluate_dataset(all_tasks, m)
                writer.writerow([m, p_h, r_orig, r_ffd_new,
                                 r_mb_new, r_cu_udp_orig])
                print(f"  P_H {p_h:.1f} done.")

    print(f"\nP_H variation saved to: {csv_ph_path}")
    print("\nAll evaluations complete.")


if __name__ == "__main__":
    main()
