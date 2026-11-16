"""Charts for the README, drawn from the pipeline's output tables."""
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img"
COLORS = {"R&D": "#2a78d6", "Manufacturing": "#eb6834", "Commercial": "#1baf7a", "Corporate IT": "#7a5cc7", "Untagged": "#898781"}
INK, MUTED, GRID, SURFACE, CRITICAL = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb", "#d03b3b"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": "#52514e", "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED,
    "font.size": 10, "legend.frameon": False,
})


def monthly_by_business_unit(con):
    rows = con.execute("""SELECT month, business_unit, SUM(effective_cost) / 1000 FROM mart_monthly_cost
                          GROUP BY 1, 2 ORDER BY 1""").fetchall()
    months = sorted({r[0] for r in rows})
    fig, ax = plt.subplots(figsize=(9, 4.4))
    bottom = [0.0] * len(months)
    for bu, color in COLORS.items():
        values = [next((v for m, b, v in rows if m == month and b == bu), 0) for month in months]
        ax.bar(months, values, bottom=bottom, color=color, label=bu, width=0.62, edgecolor=SURFACE, linewidth=1.5)
        bottom = [a + b for a, b in zip(bottom, values)]
    for x, total in zip(months, bottom):
        ax.text(x, total + 4, f"{total:.0f}k", ha="center", color=INK, fontsize=9)
    ax.set_ylabel("Effective cost [thousand USD]")
    ax.set_title("Monthly cloud cost by business unit")
    ax.set_ylim(0, max(bottom) * 1.12)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    fig.savefig(OUT / "monthly_cost.png", dpi=150)
    plt.close(fig)


def gpu_spike(con):
    daily = con.execute("""SELECT charge_date, effective_cost FROM mart_daily_cost
                           WHERE business_unit = 'R&D' AND service_category = 'AI and Machine Learning'
                           AND charge_date BETWEEN '2026-07-01' AND '2026-09-15' ORDER BY 1""").fetchall()
    flagged = con.execute("SELECT charge_date, effective_cost FROM mart_anomalies ORDER BY 1").fetchall()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot([d for d, _ in daily], [c for _, c in daily], color=COLORS["R&D"], lw=2)
    ax.scatter([d for d, _ in flagged], [c for _, c in flagged], color=CRITICAL, s=42, zorder=3, label="Flagged as anomaly")
    ax.set_ylabel("Daily cost [USD]")
    ax.set_title("R&D machine-learning cost: 9 days flagged in August")
    ax.legend(loc="upper left")
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()
    fig.savefig(OUT / "gpu_spike.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "output" / "finops.duckdb"), read_only=True)
    monthly_by_business_unit(con)
    gpu_spike(con)
    print(f"charts written to {OUT.relative_to(ROOT)}")
