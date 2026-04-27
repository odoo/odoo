# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super()._get_method_codes_using_bank_account()
        res.append('nacha')
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super()._get_method_codes_needing_bank_account()
        res.append('nacha')
        return res
