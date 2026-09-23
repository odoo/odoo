import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    rewrite_converted_domain(
        cr,
        "hr",
        "ir_rule_hr_contract_multi_company",
        "[('company_id', 'in', company_ids + [False])]",
        "[('company_id', 'in', company_ids)]",
        logger=_logger,
    )
    cr.execute(
        """
        UPDATE report_paperformat p
           SET dpi = 90,
               disable_shrinking = false
          FROM ir_model_data d
         WHERE d.model = 'report.paperformat'
           AND d.module = 'hr'
           AND d.name = 'paperformat_hr_employee_badge'
           AND d.res_id = p.id
           AND p.dpi = 96
           AND p.disable_shrinking = true
        """
    )
