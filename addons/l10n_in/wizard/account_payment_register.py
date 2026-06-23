# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'withhold' in fields_list and res['withhold'] == 'withhold_pay' and self.env.company.account_fiscal_country_id.code == 'IN':
            res['withhold'] = 'withhold'
        return res
