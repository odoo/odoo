import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)

_COMPANY_SCOPED = "[('company_id', 'in', company_ids)]"


def migrate(cr, version):
    if not version:
        return
    # the exceptional-location rule for HR users was [(1, '=', 1)], which let an HR
    # user of one company read, write and resolve the employee name of an exception
    # belonging to another; it is scoped to the user's allowed companies now
    rewrite_converted_domain(
        cr,
        "hr_homeworking",
        "homeworking_admin_rule",
        _COMPANY_SCOPED,
        "[(1, '=', 1)]",
        logger=_logger,
    )
