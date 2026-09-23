import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)

OLD_DOMAIN = "[('company_id', 'in', company_ids + [False])]"
NEW_DOMAIN = """['|', '|', '|',
            ('company_id', 'in', company_ids + [False]),
            ('employee_id.parent_id.user_id', '=', user.id),
            ('employee_id', '=', user.employee_id.parent_id.id),
            ('employee_id.user_id', '=', user.id)
        ]"""


def migrate(cr, version):
    if not version:
        return
    # the employee's rule lets a user read their manager, their reports and
    # themselves in another company; hr.employee now binds hr.version's rule
    # through version_id, so the version grants the same relationships. A
    # domain edited on the database is left as its owner wrote it
    rewrite_converted_domain(
        cr,
        "hr",
        "ir_rule_hr_contract_multi_company",
        NEW_DOMAIN,
        OLD_DOMAIN,
        logger=_logger,
    )
