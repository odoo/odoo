from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super()._get_method_codes_using_bank_account()
        res += ['enet_rtgs', 'enet_neft', 'enet_fund_transfer', 'enet_demand_draft']
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super()._get_method_codes_needing_bank_account()
        res += ['enet_rtgs', 'enet_neft', 'enet_fund_transfer', 'enet_demand_draft']
        return res
