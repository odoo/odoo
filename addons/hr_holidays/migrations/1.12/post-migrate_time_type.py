import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """A leave type's kind of time becomes the kernel record it always meant.

    `hr.leave.type.time_type` read `other` = "Worked Time" and `leave` = "Absence",
    while `resource.schedule.exception.time_type` read the same two values as
    "Other" and "Time Off" -- the same distinction under inverted labels, which is
    the defect this replaces rather than carries. Both now name a
    `resource.time.type`, whose record says what it is once.
    """
    cr.execute("""
        SELECT res_id, name
          FROM ir_model_data
         WHERE module = 'resource'
           AND name IN ('time_type_work', 'time_type_leave')
    """)
    by_name = {name: res_id for res_id, name in cr.fetchall()}
    leave, work = by_name.get("time_type_leave"), by_name.get("time_type_work")
    if not (leave and work):
        _logger.error(
            "hr_holidays 1.12: the kernel kinds of time are missing, so every leave "
            "type still has a NULL kind; resource 1.18 ships them."
        )
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'hr_leave_type' AND column_name = 'time_type'
    """)
    if not cr.fetchone():
        _logger.info("hr_holidays 1.12: no time_type column to read; nothing to map.")
        return

    cr.execute(
        """
        UPDATE hr_leave_type
           SET time_type_id = CASE WHEN time_type = 'other' THEN %s ELSE %s END
    """,
        (work, leave),
    )
    _logger.info("hr_holidays 1.12: %d leave type(s) given a kind.", cr.rowcount)
    cr.execute("ALTER TABLE hr_leave_type DROP COLUMN IF EXISTS time_type")
