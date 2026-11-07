# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _inherit = 'account.payment.register.withholding.line'

    @api.depends('payment_register_id.withhold')
    def _compute_comodel_percentage_paid_factor(self):
        """ EXTENDS 'l10n_account_withholding_tax'
        Guatemalan withholdings are applied on the full base, whatever the amount paid.
        """
        super()._compute_comodel_percentage_paid_factor()
        for wizard, lines in self.grouped('payment_register_id').items():
            if wizard.country_code == 'GT' and wizard.can_edit_wizard:
                lines.comodel_percentage_paid_factor = 1.0
