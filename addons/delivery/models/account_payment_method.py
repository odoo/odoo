# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        info = super()._get_payment_method_information()
        info['cash_on_delivery'] = {'mode': 'multi', 'type': ('bank', 'cash', 'credit')}  # TODO: what mode? which type?
        return info
