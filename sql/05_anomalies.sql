-- A day is flagged when it costs more than twice the median of the previous 28 days and at
-- least 500 USD more. The median is used because a long spike pulls an average (and standard
-- deviation) up with it: the first version, mean + 3 standard deviations over 14 days, flagged
-- only 2 of the 9 days of the August GPU spike.
CREATE OR REPLACE TABLE mart_daily_cost AS
SELECT charge_date, business_unit, service_category, ROUND(SUM(effective_cost), 2) AS effective_cost
FROM stg_billing
WHERE charge_category = 'Usage' AND commitment_status IS DISTINCT FROM 'Unused'
GROUP BY ALL;

CREATE OR REPLACE TABLE mart_anomalies AS
WITH w AS (
    SELECT *,
        quantile_cont(effective_cost, 0.5) OVER prev AS baseline,
        COUNT(*) OVER prev                           AS history_days
    FROM mart_daily_cost
    WINDOW prev AS (PARTITION BY business_unit, service_category ORDER BY charge_date
                    ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)
)
SELECT charge_date, business_unit, service_category, effective_cost,
       ROUND(baseline, 2) AS baseline, ROUND(effective_cost - baseline, 2) AS excess_cost
FROM w
WHERE history_days = 28
  AND effective_cost > 2 * baseline
  AND effective_cost - baseline >= 500
ORDER BY charge_date;
