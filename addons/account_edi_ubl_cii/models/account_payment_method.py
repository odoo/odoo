from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res.update({
            'credit_card': {'mode': 'multi', 'type': ('credit',)},
            'debit_card': {'mode': 'multi', 'type': ('credit',)},
            'bankgiro_in': {'mode': 'multi', 'type': ('bank',)},
            'bankgiro_out': {'mode': 'multi', 'type': ('bank',)},
            'standing_agreement_in': {'mode': 'multi', 'type': ('bank', 'cash', 'credit')},
            'standing_agreement_out': {'mode': 'multi', 'type': ('bank', 'cash', 'credit')},
            'sepa_credit_transfer': {'mode': 'multi', 'type': ('bank',)},
        })
        return res

    @api.model
    def _get_sdd_payment_method_code(self):
        res = super()._get_sdd_payment_method_code()
        return res
