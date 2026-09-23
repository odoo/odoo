import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    rewrite_converted_domain(
        cr,
        "hr_timesheet_attendance",
        "hr_timesheet_attendance_report_rule_approver",
        '[(1, "=", 1)]',
        logger=_logger,
    )
