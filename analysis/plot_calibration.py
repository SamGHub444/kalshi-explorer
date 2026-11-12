"""
Plot 24h calibration curves per category from the dbt mart.

Reads calibration_by_category_24h from BigQuery and saves a small-multiples
chart (one panel per category) to images/calibration_24h.png.

Run from the repo root after `dbt build`:
    python analysis/plot_calibration.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from google.cloud import bigquery

# --- Settings ----------------------------------------------------------------

PROJECT_ID = "kalshi-explorer"
TABLE = "kalshi-explorer.dbt_kalshi_dev.calibration_by_category_24h"

MIN_BUCKET_SIZE = 30      # hide buckets with fewer markets than this (too noisy)
MIN_BUCKETS = 5           # a category needs this many buckets to draw a curve
MAX_CATEGORIES = 6        # one panel per category, largest categories first
OUTPUT = Path("images/calibration_24h.png")

# Colors (validated default palette: series blue, neutral ink, muted grid)
SERIES = "#2a78d6"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"


# --- Data --------------------------------------------------------------------

def load_calibration():
    """Return the mart as a DataFrame, keeping only buckets with enough markets."""
    client = bigquery.Client(project=PROJECT_ID)
    sql = f"""
        select
            category,
            cast(probability_bucket as float64) as probability_bucket,
            cast(average_predicted_probability as float64) as predicted,
            cast(actual_yes_rate as float64) as actual,
            sample_size
        from `{TABLE}`
        where sample_size >= {MIN_BUCKET_SIZE}
    """
    return client.query(sql).to_dataframe()


def top_categories(df, n):
    """Categories with enough buckets for a curve, ordered by total markets."""
    stats = df.groupby("category").agg(
        buckets=("probability_bucket", "count"), total=("sample_size", "sum"))
    stats = stats[stats["buckets"] >= MIN_BUCKETS].sort_values("total", ascending=False)
    return list(stats.head(n).index)


# --- Chart -------------------------------------------------------------------

def plot(df, categories):
    cols = min(3, len(categories))
    rows = int(np.ceil(len(categories) / cols))
    fig, axes = plt.subplots(
        rows, cols, figsize=(5 * cols, 5 * rows + 0.6), sharex=True, sharey=True,
        facecolor=SURFACE, squeeze=False,
    )

    for ax, category in zip(axes.flat, categories):
        d = df[df["category"] == category].sort_values("predicted")
        n_total = int(d["sample_size"].sum())

        # 95% interval on the actual yes rate: 1.96 * sqrt(p(1-p)/n)
        err = 1.96 * np.sqrt(d["actual"] * (1 - d["actual"]) / d["sample_size"])

        ax.set_facecolor(SURFACE)
        ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, color=MUTED,
                label="Perfect calibration")
        ax.errorbar(d["predicted"], d["actual"], yerr=err, color=SERIES,
                    linewidth=2, marker="o", markersize=6, capsize=0,
                    elinewidth=1, label="Kalshi markets")

        ax.set_title(f"{category}  (n = {n_total:,})", color=INK, fontsize=11,
                     loc="left")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.grid(color=GRID, linewidth=0.8)
        ax.tick_params(colors=MUTED, labelsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)

    # Hide empty panels if categories don't fill the grid
    for ax in axes.flat[len(categories):]:
        ax.set_visible(False)

    for ax in axes[-1]:
        ax.set_xlabel("Predicted probability (bid/ask midpoint ~24h before close)",
                      color=MUTED, fontsize=9)
    for ax in axes[:, 0]:
        ax.set_ylabel("Actual yes rate", color=MUTED, fontsize=9)

    axes.flat[0].legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("Kalshi 24h calibration by category", x=0.02, ha="left",
                 color=INK, fontsize=14)
    fig.text(0.02, 0.01,
             f"Buckets with < {MIN_BUCKET_SIZE} markets hidden; categories need "
             f"{MIN_BUCKETS}+ buckets.\nError bars: 95% interval on the yes rate "
             "(ignores correlation within events).",
             color=MUTED, fontsize=8)

    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, facecolor=SURFACE)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    data = load_calibration()
    plot(data, top_categories(data, MAX_CATEGORIES))
