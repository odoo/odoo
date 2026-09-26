# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _get_default_withhold(self, moves):
        """ For any tax that has withholding enabled, PH always withholds and pays: unlike the
        generic default (which can leave the withholding for a later, withhold-only payment),
        the withholding tax must be recognized together with the payment so it lands on the
        correct BIR tax report as soon as the transaction is settled. """
        if moves and moves[0].company_id.account_fiscal_country_id.code == 'PH':
            if sum(moves.mapped('withholding_residual_amount_currency')) > 0:
                return 'withhold_pay'
        return super()._get_default_withhold(moves)
