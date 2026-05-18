"""
Plot the offline schedulability results (paper Section 4.2).

Reads the CSVs produced by offline_schedulability.py and generates one
acceptance-ratio figure per processor count:

    Figure 3  - acceptance ratio vs. target utilization per core
                (from simulation_results.csv)
    Figure 4  - acceptance ratio vs. HC-task probability P_H
                (from simulation_ph_results.csv)
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from config import RESULT_DIR

# Column name -> (legend label, marker, linestyle, color)
ALGO_STYLES = {
    "FFD_base":    ("FFD(base)",    "o", "-",  "#2ca02c"),
    "IMC_PALM_v1": ("IMC-PALM(v1)", "s", "--", "#1f77b4"),
    "IMC_PALM_v2": ("IMC-PALM(v2)", "x", "-",  "#d62728"),
    "CU_UDP":      ("CU-UDP",       "^", "-",  "#2ca02c"),
}


def _plot(df, x_col, x_label, prefix, result_dir):
    for m in sorted(df["m"].unique()):
        sub = df[df["m"] == m].sort_values(x_col)

        plt.figure(figsize=(6, 4))
        for col, (label, marker, ls, color) in ALGO_STYLES.items():
            if col not in sub.columns:
                continue
            plt.plot(sub[x_col], sub[col], label=label, marker=marker,
                     linestyle=ls, markersize=6, linewidth=1.8)

        plt.xlabel(x_label, fontsize=12)
        plt.ylabel("Acceptance Ratio (%)", fontsize=12)
        plt.title(f"m = {m} processors", fontsize=13)
        plt.ylim(-2, 105)
        plt.xticks(sub[x_col])
        plt.legend(fontsize=10, loc="best")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        pdf_filename = f"{prefix}_m{m}.pdf"
        pdf_file_path = os.path.join(result_dir, pdf_filename)
        plt.savefig(pdf_file_path, format="pdf", bbox_inches="tight")
        plt.close()
        print(f"  Saved: {pdf_filename}")


def plot_util(result_dir):
    """Figure 3: acceptance ratio vs. target utilization."""
    csv_path = os.path.join(result_dir, "simulation_results.csv")
    if not os.path.exists(csv_path):
        print(f"[skip] CSV not found: {csv_path}")
        return
    df = pd.read_csv(csv_path)
    print("[Fig3] acceptance ratio vs. target utilization")
    _plot(df, "Target", "Target Utilization / Core",
          "acceptance_ratio_util", result_dir)


def plot_ph(result_dir):
    """Figure 4: acceptance ratio vs. HC-task probability."""
    csv_path = os.path.join(result_dir, "simulation_ph_results.csv")
    if not os.path.exists(csv_path):
        print(f"[skip] CSV not found: {csv_path}")
        return
    df = pd.read_csv(csv_path)
    print("[Fig4] acceptance ratio vs. HC-task probability P_H")
    _plot(df, "P_H", "Probability of HC Task (P_H)",
          "acceptance_ratio_ph", result_dir)


def main():
    plot_util(RESULT_DIR)
    plot_ph(RESULT_DIR)
    print("\nDone!")


if __name__ == "__main__":
    main()
