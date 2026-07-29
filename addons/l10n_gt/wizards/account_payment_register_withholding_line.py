# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _inherit = 'account.payment.register.withholding.line'

    @api.depends('payment_register_id.withhold')
    def _compute_comodel_percentage_paid_factor(self):
        """ EXTENDS 'l10n_account_withholding_tax'
        The generic withholding-only factor prorates on withholding taxes declared
        on the invoice lines, which Guatemala doesn't set.
        """
        super()._compute_comodel_percentage_paid_factor()
        for wizard, lines in self.grouped('payment_register_id').items():
            if wizard.country_code != 'GT' or wizard.withhold != 'withhold':
                continue

            residual_amount = wizard._get_total_amounts_to_pay(wizard._get_batches())['full_amount']
            invoice_amount = wizard._get_total_amount_in_wizard_currency()
            lines.comodel_percentage_paid_factor = (
                abs(residual_amount / invoice_amount) if residual_amount and invoice_amount else 1.0
            )
