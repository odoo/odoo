import logging

_logger = logging.getLogger(__name__)


def _fill_flow_state(cr):
    cr.execute(
        "ALTER TABLE approval_approver ADD COLUMN IF NOT EXISTS flow_state varchar"
    )
    cr.execute(
        """
        UPDATE approval_approver
           SET flow_state = CASE
                   WHEN state IN ('new', 'pending', 'waiting', 'cancelled') THEN state
                   WHEN state = 'refused' AND decision_date IS NULL THEN 'refused'
                   ELSE 'waiting'
               END
         WHERE flow_state IS NULL
        """
    )


def _record_decisions_the_ledger_never_saw(cr):
    cr.execute(
        """
        CREATE TEMP TABLE approval_unrecorded_decision ON COMMIT DROP AS
        WITH last_reset AS (
            SELECT request_id, max(id) AS id
              FROM approval_decision_log
             WHERE verdict = 'reset'
             GROUP BY request_id
        )
        SELECT row.id AS approver_id
          FROM approval_approver row
     LEFT JOIN last_reset ON last_reset.request_id = row.request_id
         WHERE (
                   row.state = 'approved'
                OR (row.state = 'refused' AND row.decision_date IS NOT NULL)
               )
           AND NOT EXISTS (
                   SELECT 1
                     FROM approval_decision_log fact
                    WHERE fact.approver_id = row.id
                      AND fact.verdict IN ('approved', 'refused', 'withdrawn')
                      AND fact.id > COALESCE(last_reset.id, 0)
               )
        """
    )
    cr.execute(
        """
        WITH inserted AS (
            INSERT INTO approval_decision_log (
                request_id, company_id, approver_id, verdict, state_after, user_id,
                elevation, refusal_reason_id, note, date,
                create_uid, write_uid, create_date, write_date
            )
            SELECT row.request_id, request.company_id, row.id, row.state,
                   request.state, COALESCE(row.decided_by_user_id, row.user_id),
                   'none', row.refusal_reason_id, row.note,
                   COALESCE(row.decision_date, row.write_date,
                            now() AT TIME ZONE 'UTC'),
                   1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
              FROM approval_unrecorded_decision unrecorded
              JOIN approval_approver row ON row.id = unrecorded.approver_id
              JOIN approval_request request ON request.id = row.request_id
         RETURNING id, approver_id
        )
        INSERT INTO approval_decision_log_step_rel (
            approval_decision_log_id, approval_category_step_id
        )
        SELECT inserted.id, decided.step_id
          FROM inserted
          JOIN approval_approver_decided_step_rel decided
            ON decided.approver_id = inserted.approver_id
        """
    )
    cr.execute("SELECT count(*) FROM approval_unrecorded_decision")
    _logger.info(
        "approval 2.7: recorded %s decision(s) the ledger never saw, so the "
        "approvers' status stays what it was once it is read from the ledger",
        cr.fetchone()[0],
    )


def migrate(cr, version):
    _fill_flow_state(cr)
    _record_decisions_the_ledger_never_saw(cr)
