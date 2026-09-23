import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_LEGACY_COLUMNS = ("state", "reviewed_by_uid", "reviewed_on", "refusal_reason")


def migrate(cr, version):
    """Give every change request already on file the approval request it would
    have raised, and carry the decision it already had.

    The hand-written pending/approved/refused machine is gone. Its columns are
    still on the table at post-migrate time -- the registry drops them at the end
    of the load, after this runs -- so they are read here and nowhere else. A row
    whose approval cannot be raised (no category, no approver) is left with no
    request rather than failing the upgrade, and says so in the log.
    """
    if not version:
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'hr_employee_change_request'
           AND column_name = ANY(%s)
        """,
        [list(_LEGACY_COLUMNS)],
    )
    if not cr.fetchall():
        return

    cr.execute(
        """
        SELECT id, state, refusal_reason
          FROM hr_employee_change_request
         WHERE approval_request_id IS NULL
         ORDER BY id
        """
    )
    rows = cr.fetchall()
    if not rows:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    Request = env["hr.employee.change.request"]
    raised = decided = skipped = 0
    for record_id, state, refusal_reason in rows:
        record = Request.browse(record_id)
        try:
            record.action_create_approval_request()
        except Exception as exc:
            skipped += 1
            _logger.warning(
                "hr 1.21: change request %s kept without an approval request: %s",
                record_id,
                exc,
                exc_info=True,
            )
            continue
        raised += 1
        approval = record.approval_request_id
        if state == "approved":
            approval._approve_without_decision(
                env._(
                    "Approved before this record was moved onto the approval "
                    "engine; the decision is carried, not re-asked."
                )
            )
            decided += 1
        elif state == "refused":
            approval._force_terminal(
                "refused",
                env._(
                    "Refused before this record was moved onto the approval "
                    "engine; the decision is carried, not re-asked."
                ),
                refusal_note=refusal_reason or None,
            )
            decided += 1
    _logger.info(
        "hr 1.21: %d change request(s) given an approval request, %d of them "
        "already decided, %d left without one.",
        raised,
        decided,
        skipped,
    )
