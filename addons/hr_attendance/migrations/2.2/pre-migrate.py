import logging

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)

_REMOVED = (
    ("overtime_company_threshold", "employer_tolerance"),
    ("overtime_employee_threshold", "employee_tolerance"),
)


def migrate(cr, version):
    """Report the company-level overtime tolerances before they go.

    `overtime_company_threshold` and `overtime_employee_threshold` were minutes
    of excess and of shortfall to ignore, set on `res.company`. Nothing has read
    them since the rule engine landed: a tolerance is now `employer_tolerance`
    and `employee_tolerance` on each `hr.attendance.overtime.rule`, which is
    where it has to live once different rules can price the same hour
    differently.

    This does not drop the columns. `ir.model.fields._drop_columns()` already
    does, when the module's field records are cleaned up during the upgrade --
    which is also why this runs in `pre` and not in `post`: by `post` the
    column is gone and there is nothing left to read. What the ORM cannot do is
    say that a company had set one, and a company that had is entitled to know
    the setting is not carried over. It is not carried over because there is no
    single rule to carry it to, and picking one would be a guess about which of
    an employee's rules the company meant.
    """
    if not version:
        return
    for column, replacement in _REMOVED:
        if not column_exists(cr, "res_company", column):
            continue
        cr.execute(
            f'SELECT id, "{column}" FROM res_company '
            f'WHERE "{column}" IS NOT NULL AND "{column}" != 0'
        )
        for company_id, value in cr.fetchall():
            _logger.warning(
                "hr_attendance: company %s had %s = %s minutes. That setting is "
                "removed and is not carried over; set %s on the overtime rules "
                "its rulesets carry instead.",
                company_id,
                column,
                value,
                replacement,
            )
