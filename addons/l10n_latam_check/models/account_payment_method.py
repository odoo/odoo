from odoo import models, api
from odoo.addons import account


class AccountPaymentMethod(account.AccountPaymentMethod):

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['new_third_party_checks'] = {'mode': 'multi', 'type': ('cash',)}
        res['in_third_party_checks'] = {'mode': 'multi', 'type': ('cash',)}
        res['out_third_party_checks'] = {'mode': 'multi', 'type': ('cash',)}
        res['own_checks'] = {'mode': 'multi', 'type': ('bank',)}
        return res
