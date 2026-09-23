import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    rewrite_converted_domain(
        cr,
        "hr_holidays",
        "hr_leave_allocation_rule_multicompany",
        '["|", ("employee_id", "=", False), ("employee_id.company_id", "in", '
        'company_ids), "|", ("holiday_status_id.company_id", "=", False), '
        '("holiday_status_id.company_id", "in", company_ids)]',
        logger=_logger,
    )
