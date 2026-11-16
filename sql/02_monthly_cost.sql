CREATE OR REPLACE TABLE mart_monthly_cost AS
SELECT
    month, provider, business_unit, environment, service_category,
    ROUND(SUM(effective_cost), 2)              AS effective_cost,
    ROUND(SUM(billed_cost), 2)                 AS billed_cost,
    ROUND(SUM(list_cost), 2)                   AS list_cost,
    ROUND(SUM(list_cost - effective_cost) FILTER (WHERE charge_category = 'Usage'
          AND commitment_status IS DISTINCT FROM 'Unused'), 2) AS discount_savings
FROM stg_billing
GROUP BY ALL
ORDER BY month, effective_cost DESC;
