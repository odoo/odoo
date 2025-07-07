from odoo import models


class ChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo, force_create=True):
        super()._load(template_code, company, install_demo, force_create)
        if template_code == 'sa':
            manual_payment_method = self.env.ref('account.account_payment_method_manual_out')
            manual_payment_method_lines = self.env['account.payment.method.line'].search([
                ('payment_method_id', '=', manual_payment_method.id),
            ])
            manual_payment_method_lines.write({
                'payment_account_id': self.env.ref(f'account.{company.id}_account_journal_payment_credit_account_id').id,
            })
