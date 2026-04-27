# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _action_tax_to_pay_wizard(self):
        # EXTENDS account_reports
        payable_tax = self._get_tax_to_pay_on_closing()
        if self.company_id.account_fiscal_country_id.code == 'NL' and payable_tax > 0:
            return self.env['l10n_nl.vat.pay.wizard'].create({
                'move_id': self.id,
                'amount': payable_tax,
            }).with_context({
                'dialog_size': 'medium',
            })._get_records_action(
                name=_("VAT Payment"),
                target='new',
            )
        return super()._action_tax_to_pay_wizard()
