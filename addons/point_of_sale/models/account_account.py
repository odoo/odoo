from odoo import api, models


class AccountAccount(models.Model):
    _name = 'account.account'
    _inherit = ['account.account', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'id', 'non_trade',
        ]

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['res.partner'].property_account_receivable_id.ids)]
