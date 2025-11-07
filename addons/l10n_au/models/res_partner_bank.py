import re

from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_type = fields.Selection(selection_add=[('aba', 'ABA')])

    @api.model
    def retrieve_account_type(self, account_number):
        account_type = super().retrieve_account_type(account_number)
        if account_type == 'bank' and re.match(r"^(?=.*[1-9])[ \-\d]{0,9}$", account_number or ''):
            return 'aba'
        return account_type
