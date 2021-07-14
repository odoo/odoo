from odoo import models, _
import logging
_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _create_bank_journals(self, company, acc_template_ref):
        res = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)

        if company.country_id.code == "AR":
            self.env['account.journal'].create({
                'name': _('Third Checks'),
                'type': 'cash',
                'company_id': company.id,
                'inbound_payment_method_ids': [
                    (4, self.env.ref('l10n_ar_third_check.account_payment_method_new_third_checks').id, None),
                ],
                'outbound_payment_method_ids': [
                    (4, self.env.ref('l10n_ar_third_check.account_payment_method_out_third_checks').id, None),
                ],
            })
            self.env['account.journal'].create({
                'name': _('Rejected Third Checks'),
                'type': 'cash',
                'company_id': company.id,
                'inbound_payment_method_ids': [
                    (4, self.env.ref('l10n_ar_third_check.account_payment_method_in_third_checks').id, None),
                ],
                'outbound_payment_method_ids': [
                    (4, self.env.ref('l10n_ar_third_check.account_payment_method_out_third_checks').id, None),
                ],
            })

        return res
