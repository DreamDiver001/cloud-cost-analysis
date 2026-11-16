CREATE OR REPLACE TABLE mart_kpis AS
WITH m AS (
    SELECT month, SUM(effective_cost) AS cost FROM stg_billing GROUP BY month
), last AS (
    SELECT MAX(month) AS month FROM m
), prev AS (
    SELECT MAX(month) AS month FROM m WHERE month < (SELECT month FROM last)
)
SELECT 'Effective cost, last month (USD)' AS kpi, ROUND((SELECT cost FROM m WHERE month = (SELECT month FROM last)), 0) AS value
UNION ALL SELECT 'Change vs previous month (%)',
    ROUND(100 * ((SELECT cost FROM m WHERE month = (SELECT month FROM last)) /
                 (SELECT cost FROM m WHERE month = (SELECT month FROM prev)) - 1), 1)
UNION ALL SELECT 'Tag coverage, last month (%)',
    (SELECT tag_coverage_pct FROM mart_tag_coverage WHERE month = (SELECT month FROM last))
UNION ALL SELECT 'Untagged cost, 6 months (USD)', ROUND((SELECT SUM(untagged_cost) FROM mart_tag_coverage), 0)
UNION ALL SELECT 'AWS commitment coverage of compute, 6 months (%)',
    ROUND((SELECT AVG(compute_coverage_pct) FROM mart_commitments WHERE provider = 'AWS'), 1)
UNION ALL SELECT 'Azure reservation utilisation, 6 months (%)',
    ROUND((SELECT 100 * SUM(used) / SUM(used + unused) FROM mart_commitments WHERE provider = 'Microsoft'), 1)
UNION ALL SELECT 'Unused commitment, 6 months (USD)', ROUND((SELECT SUM(unused) FROM mart_commitments), 0)
UNION ALL SELECT 'Cost anomalies flagged (days)', (SELECT COUNT(*) FROM mart_anomalies)
UNION ALL SELECT 'Excess cost on anomaly days (USD)', ROUND((SELECT COALESCE(SUM(excess_cost), 0) FROM mart_anomalies), 0)
UNION ALL SELECT 'Always-on non-prod VMs', (SELECT COUNT(*) FROM mart_always_on)
UNION ALL SELECT 'Saving if they ran 12h on weekdays, per year (USD)', ROUND((SELECT SUM(savings_6m_if_scheduled) FROM mart_always_on) * 2, 0);
