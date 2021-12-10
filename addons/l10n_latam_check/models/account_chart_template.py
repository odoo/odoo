from odoo import models, _
import logging
_logger = logging.getLogger(__name__)
THIRD_CHECKS_COUNTRY_CODES = ["AR"]


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _create_bank_journals(self, company, acc_template_ref):
        res = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)

        if company.country_id.code in THIRD_CHECKS_COUNTRY_CODES:
            self.env['account.journal'].with_context(third_checks_journal=True).create({
                'name': _('Third Checks'),
                'type': 'cash',
                'company_id': company.id,
            })
            self.env['account.journal'].with_context(third_checks_journal=True).create({
                'name': _('Rejected Third Checks'),
                'type': 'cash',
                'company_id': company.id,
            })

        return res
