from odoo import models, api


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['new_third_party_checks'] = {'mode': 'multi', 'domain': [('type', '=', 'cash')]}
        res['in_third_party_checks'] = {'mode': 'multi', 'domain': [('type', '=', 'cash')]}
        res['out_third_party_checks'] = {'mode': 'multi', 'domain': [('type', '=', 'cash')]}
        return res
