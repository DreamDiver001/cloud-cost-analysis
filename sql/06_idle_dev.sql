-- Non-production compute that costs as much at weekends as on weekdays is never switched off.
-- Savings assume a 12-hour weekday schedule: 60 of 168 hours a week.
CREATE OR REPLACE TABLE mart_always_on AS
WITH per_resource AS (
    SELECT provider, sub_account, resource_id, business_unit, environment,
        AVG(effective_cost) FILTER (WHERE is_weekend)      AS weekend_daily,
        AVG(effective_cost) FILTER (WHERE NOT is_weekend)  AS weekday_daily,
        SUM(effective_cost)                                AS cost_6m
    FROM stg_billing
    WHERE charge_category = 'Usage' AND service_category = 'Compute' AND environment <> 'prod'
    GROUP BY ALL
)
SELECT provider, sub_account, resource_id, business_unit, environment,
    ROUND(weekend_daily / NULLIF(weekday_daily, 0), 2)  AS weekend_to_weekday,
    ROUND(cost_6m, 2)                                   AS cost_6m,
    ROUND(cost_6m * (1 - 60.0 / 168), 2)                AS savings_6m_if_scheduled
FROM per_resource
WHERE weekend_daily / NULLIF(weekday_daily, 0) > 0.9
ORDER BY savings_6m_if_scheduled DESC;
