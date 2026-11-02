# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS account
        # The withholding of a POS bank payment, see pos.payment.method._create_bank_payment_line.
        if withholding_vals := self.env.context.get('l10n_ph_pos_withholding_payment_vals'):
            for vals in vals_list:
                if vals.get('pos_payment_method_id'):
                    vals.update(withholding_vals)
        return super().create(vals_list)
