-- Utilisation: share of the commitment that was actually used.
-- Coverage: share of compute usage (at list price) that ran under a commitment.
CREATE OR REPLACE TABLE mart_commitments AS
WITH c AS (
    SELECT provider, month,
        SUM(effective_cost) FILTER (WHERE commitment_status = 'Used')    AS used,
        SUM(effective_cost) FILTER (WHERE commitment_status = 'Unused')  AS unused,
        SUM(billed_cost) FILTER (WHERE charge_category = 'Purchase')     AS fee,
        SUM(list_cost) FILTER (WHERE commitment_status = 'Used')         AS covered_list,
        SUM(list_cost) FILTER (WHERE charge_category = 'Usage' AND service_category = 'Compute'
                               AND commitment_status IS DISTINCT FROM 'Unused') AS compute_list,
        SUM(list_cost - effective_cost) FILTER (WHERE commitment_status = 'Used') AS savings
    FROM stg_billing
    GROUP BY provider, month
)
SELECT provider, month,
    ROUND(fee, 2)                                           AS commitment_fee,
    ROUND(COALESCE(used, 0), 2)                             AS used,
    ROUND(COALESCE(unused, 0), 2)                           AS unused,
    ROUND(100 * COALESCE(used, 0) / NULLIF(COALESCE(used, 0) + COALESCE(unused, 0), 0), 1) AS utilisation_pct,
    ROUND(100 * covered_list / NULLIF(compute_list, 0), 1)  AS compute_coverage_pct,
    ROUND(COALESCE(savings, 0), 2)                          AS savings_vs_list
FROM c
ORDER BY provider, month;
