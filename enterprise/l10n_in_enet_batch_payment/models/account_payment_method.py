from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        for code in ['enet_rtgs', 'enet_neft', 'enet_fund_transfer', 'enet_demand_draft']:
            res[code] = {
                'mode': 'multi',
                'type': ('bank',),
                'country_id': self.env.ref("base.in").id,
            }
        return res
