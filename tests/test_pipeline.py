from datetime import date, timedelta

from pipeline.quality import run_checks


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_all_quality_checks_pass_on_the_sample(con):
    assert all(ok for _, ok in run_checks(con))


def test_marts_reconcile_with_the_source(con):
    src = scalar(con, "SELECT SUM(effective_cost) FROM stg_billing")
    assert abs(scalar(con, "SELECT SUM(effective_cost) FROM mart_monthly_cost") - src) < 1
    usage = scalar(con, """SELECT SUM(effective_cost) FROM stg_billing
                           WHERE charge_category = 'Usage' AND commitment_status IS DISTINCT FROM 'Unused'""")
    assert abs(scalar(con, "SELECT SUM(usage_cost) FROM mart_tag_coverage") - usage) < 1


def test_resources_without_business_unit_tag_count_as_untagged(con):
    assert scalar(con, "SELECT COUNT(*) FROM stg_billing WHERE business_unit = ''") == 0
    assert scalar(con, "SELECT COUNT(DISTINCT resource_id) FROM mart_untagged_resources") == 11


def test_the_august_gpu_spike_is_flagged_on_every_day_and_nothing_else(con):
    days = [r[0] for r in con.execute("SELECT charge_date FROM mart_anomalies ORDER BY 1").fetchall()]
    assert days == [date(2026, 8, 11) + timedelta(days=i) for i in range(9)]
    assert scalar(con, "SELECT COUNT(DISTINCT service_category) FROM mart_anomalies") == 1


def test_scheduled_dev_machines_are_not_reported_as_always_on(con):
    assert scalar(con, "SELECT COUNT(*) FROM mart_always_on WHERE resource_id LIKE '%rnd-dev%'") == 0
    assert scalar(con, "SELECT COUNT(*) FROM mart_always_on WHERE environment = 'prod'") == 0


def test_commitment_metrics(con):
    aws = scalar(con, "SELECT MIN(utilisation_pct) FROM mart_commitments WHERE provider = 'AWS'")
    azure = scalar(con, "SELECT 100 * SUM(used) / SUM(used + unused) FROM mart_commitments WHERE provider = 'Microsoft'")
    assert aws == 100.0
    assert 65 < azure < 75


def test_purchases_are_not_counted_twice(con):
    fees = scalar(con, "SELECT SUM(billed_cost) FROM stg_billing WHERE charge_category = 'Purchase'")
    amortised = scalar(con, "SELECT SUM(effective_cost) FROM stg_billing WHERE commitment_status IN ('Used', 'Unused')")
    assert abs(fees - amortised) < 1
    assert scalar(con, "SELECT SUM(effective_cost) FROM stg_billing WHERE charge_category = 'Purchase'") == 0
