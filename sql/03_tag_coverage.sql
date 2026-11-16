-- Coverage is measured on resource usage. Commitment fees, unused commitment and credits are
-- allocated centrally and would make coverage look better than it is.
CREATE OR REPLACE TABLE mart_tag_coverage AS
WITH usage AS (
    SELECT * FROM stg_billing
    WHERE charge_category = 'Usage' AND commitment_status IS DISTINCT FROM 'Unused'
)
SELECT
    month,
    ROUND(SUM(effective_cost), 2)                                            AS usage_cost,
    ROUND(SUM(effective_cost) FILTER (WHERE business_unit = 'Untagged'), 2)  AS untagged_cost,
    ROUND(100 * (1 - SUM(effective_cost) FILTER (WHERE business_unit = 'Untagged') / SUM(effective_cost)), 1) AS tag_coverage_pct,
    COUNT(DISTINCT resource_id) FILTER (WHERE business_unit = 'Untagged')    AS untagged_resources
FROM usage
GROUP BY month
ORDER BY month;

CREATE OR REPLACE TABLE mart_untagged_resources AS
SELECT provider, sub_account, resource_id, service_category, environment,
       ROUND(SUM(effective_cost), 2) AS effective_cost_6m
FROM stg_billing
WHERE business_unit = 'Untagged' AND charge_category = 'Usage'
GROUP BY ALL
ORDER BY effective_cost_6m DESC;
