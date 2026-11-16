import csv
from pathlib import Path

from pipeline.quality import run_checks
from pipeline.run import build

ROOT = Path(__file__).resolve().parent.parent


def small_export(tmp_path, change):
    with open(ROOT / "data" / "focus_billing.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))[:400]
    change(rows)
    path = tmp_path / "bad.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return dict(run_checks(build(path)))


def usage_row(rows):
    return next(r for r in rows if r["ChargeCategory"] == "Usage" and r["PricingCategory"] == "Standard")


def test_second_currency_is_caught(con, tmp_path):
    result = small_export(tmp_path, lambda rows: usage_row(rows).update(BillingCurrency="EUR"))
    assert result["one billing currency"] is False


def test_negative_usage_is_caught(con, tmp_path):
    result = small_export(tmp_path, lambda rows: usage_row(rows).update(BilledCost="-50", EffectiveCost="-50"))
    assert result["no negative usage costs"] is False


def test_committed_row_without_commitment_is_caught(con, tmp_path):
    def change(rows):
        r = next(r for r in rows if r["PricingCategory"] == "Committed")
        r["CommitmentDiscountId"] = ""
    assert small_export(tmp_path, change)["committed rows name their commitment"] is False


def test_charge_outside_billing_period_is_caught(con, tmp_path):
    result = small_export(tmp_path, lambda rows: usage_row(rows).update(ChargePeriodStart="2026-04-30"))
    assert result["every charge falls inside its billing period"] is False


def test_duplicated_line_is_caught(con, tmp_path):
    result = small_export(tmp_path, lambda rows: rows.append(dict(usage_row(rows))))
    assert result["no duplicate charge lines"] is False
