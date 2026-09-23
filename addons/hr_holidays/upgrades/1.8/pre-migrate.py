import logging

from odoo.addons.base.models.ir_access_convert import converted_row_ids

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    ids = converted_row_ids(
        cr, "hr_holidays", "hr_leav_allocation_rule_employee_unlink"
    )
    cr.execute(
        """
        UPDATE ir_access
           SET domain = '[("employee_id.user_id", "=", user.id), ("state", "=", "confirm")]'
         WHERE id = ANY(%s) AND domain LIKE '%%''draft''%%'
        """,
        [ids],
    )
    _logger.info(
        "hr_leav_allocation_rule_employee_unlink: %s of %s row(s) rewritten",
        cr.rowcount,
        len(ids),
    )
