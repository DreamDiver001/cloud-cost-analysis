CHECKS = [
    ("one billing currency",
     "SELECT COUNT(DISTINCT currency) = 1 FROM stg_billing"),
    ("every charge falls inside its billing period",
     "SELECT COUNT(*) = 0 FROM stg_billing WHERE charge_date < billing_period_start OR charge_date >= billing_period_end"),
    ("no negative usage costs",
     "SELECT COUNT(*) = 0 FROM stg_billing WHERE charge_category = 'Usage' AND (billed_cost < 0 OR effective_cost < 0)"),
    ("committed rows name their commitment",
     "SELECT COUNT(*) = 0 FROM stg_billing WHERE pricing_category = 'Committed' AND COALESCE(commitment_id, '') = ''"),
    ("billed and effective cost reconcile over the period (within 1 USD)",
     "SELECT ABS(SUM(billed_cost) - SUM(effective_cost)) < 1 FROM stg_billing"),
    ("monthly mart adds up to the source data",
     "SELECT ABS((SELECT SUM(effective_cost) FROM mart_monthly_cost) - (SELECT SUM(effective_cost) FROM stg_billing)) < 1"),
    ("no duplicate charge lines",
     """SELECT COUNT(*) = 0 FROM (
          SELECT resource_id, charge_date, pricing_category, charge_category, charge_description, COUNT(*) n
          FROM stg_billing GROUP BY ALL HAVING n > 1)"""),
]


def run_checks(con) -> list[tuple[str, bool]]:
    return [(name, bool(con.execute(sql).fetchone()[0])) for name, sql in CHECKS]
