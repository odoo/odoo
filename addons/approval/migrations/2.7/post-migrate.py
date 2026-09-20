import logging

_logger = logging.getLogger(__name__)


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
                request_id, approver_id, verdict, state_after, user_id,
                elevation, refusal_reason_id, note, date,
                create_uid, write_uid, create_date, write_date
            )
            SELECT row.request_id, row.id, row.state,
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
    """Give every standing decision a ledger fact, once the ledger exists."""
    # An approver's status is projected from approval.decision.log, so a row
    # approved before the ledger existed would read as merely waiting once it
    # is recomputed. This ran as a pre-migration until a database upgrading
    # from below 19.0.2.1.0 (where the ledger model first appeared) met it
    # before the models were loaded and the table created. A post-migration
    # sees the table on both paths: from 2.6, where it already existed, and
    # from any earlier version, where the load just created it.
    _record_decisions_the_ledger_never_saw(cr)
