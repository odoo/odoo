-- =============================================================================
-- tune_threshold.sql
--
-- Week-7 milestone: pick the confidence threshold that keeps false
-- auto-approvals near zero.
--
-- The global routing threshold (invoice_agent.confidence_threshold) decides
-- which extracted bills ride the "Auto" kanban column and which land in
-- "Needs Review". Raising it costs human review hours; lowering it risks
-- shipping a wrong number into a draft. We compute the trade-off directly
-- off production data:
--
--   * "approved"  = a bill that cleared the threshold (ai_extraction_state
--                   in ('auto','approved')) OR any AI-processed bill when
--                   you want the full population.
--   * "error"     = a bill whose final posted/validated truth disagrees with
--                   what the AI extracted: extracted_total diverges from the
--                   real total, or the human had to touch the review flag,
--                   or the AI itself failed (status = 'failed').
--
-- Thresholds probed: 0.70 / 0.80 / 0.90 (the brief's three values). The
-- same shape as the "Calibrated blend" table the eval script prints over
-- the golden set (scripts/eval_extraction.py --curve), but computed over
-- real volume by joining the usage ledger (invoice_agent_usage, one row per
-- Claude call) to the move it produced.
--
-- Run against the production DB:
--
--     docker compose exec db psql -U odoo -d odoo \
--         -f custom_addons/invoice_agent/scripts/tune_threshold.sql
--
-- Interpreting the output:
--   * zero false auto-approvals everywhere -> pick the HIGHEST threshold
--     still at or above the target auto-approval rate.
--   * errors at 0.80 but none at 0.90 -> commit 0.90 as the config default.
--   * errors even at 0.90 -> the calibrated score is not discriminating; do
--     NOT just raise the threshold, re-tune the confidence weights
--     (models/confidence.py) and re-run the eval instead.
-- =============================================================================

-- All AI-processed moves (one row per move, deduplicated by usage row).
WITH ai_moves AS (
    SELECT DISTINCT
        am.id,
        am.move_type,
        am.state,
        am.amount_total,
        am.ai_extracted_total,
        am.ai_extraction_status,
        am.ai_extraction_state,
        am.confidence_score,
        am.ai_review_required,
        am.ai_extracted_on
    FROM account_move am
    JOIN invoice_agent_usage usage
      ON usage.move_id = am.id
    WHERE am.move_type = 'in_invoice'
      AND am.ai_extraction_status IN ('extracted', 'validated', 'failed')
),

-- A bill is an "error" when the AI result was never trusted/successful:
--   * the pipeline itself failed, or
--   * the human had to flag it for review, or
--   * the AI total materially disagrees with the real total (> 1% or > 1 unit).
scored AS (
    SELECT
        id,
        confidence_score,
        CASE
            WHEN ai_extraction_status = 'failed' THEN 1
            WHEN ai_review_required THEN 1
            WHEN ai_extracted_total IS NULL
                 OR amount_total IS NULL THEN 1
            WHEN ABS(ai_extracted_total - amount_total) > 1.0
                 AND (amount_total = 0
                      OR ABS(ai_extracted_total - amount_total) / amount_total > 0.01)
                 THEN 1
            ELSE 0
        END AS is_error
    FROM ai_moves
    WHERE confidence_score IS NOT NULL
)

-- One row per probed threshold: how many bills would ride Auto, and how many
-- of those are errors (false auto-approvals).
SELECT
    threshold.value                           AS threshold_value,
    COUNT(*) FILTER (WHERE s.confidence_score >= threshold.value)
                                             AS auto_approved,
    COUNT(*) FILTER (WHERE s.confidence_score >= threshold.value AND is_error = 1)
                                             AS false_auto_approvals,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE s.confidence_score >= threshold.value) / COUNT(*),
        1
    )                                        AS auto_approval_rate_pct,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE s.confidence_score >= threshold.value AND is_error = 1)
        / NULLIF(COUNT(*) FILTER (WHERE s.confidence_score >= threshold.value), 0),
        1
    )                                        AS error_rate_among_approved_pct
FROM scored s
CROSS JOIN LATERAL (
    VALUES (0.70::float8), (0.80::float8), (0.90::float8)
) AS threshold(value)
GROUP BY threshold.value
ORDER BY threshold.value;

-- -----------------------------------------------------------------------------
-- Optional follow-up (uncomment to inspect the worst offenders):
-- -----------------------------------------------------------------------------
-- SELECT id, move_type, amount_total, ai_extracted_total,
--        ai_extraction_status, ai_extraction_state, confidence_score
-- FROM account_move
-- WHERE ai_extraction_status IN ('extracted', 'validated', 'failed')
--   AND ai_review_required = true
-- ORDER BY confidence_score ASC
-- LIMIT 20;

-- === Choose the threshold and commit it (zero-downtime, no redeploy) ===
-- UPDATE ir_config_parameter
--    SET value = '0.90'
--  WHERE key = 'invoice_agent.confidence_threshold';
--
-- The kanban re-routes existing moves immediately (res_config_settings
-- set_values recomputes the routing on save). Rollback = set the value back
-- to '0.80' with the same one-line UPDATE — the version control releases notes
-- document this as the v0.7 rollback path.
