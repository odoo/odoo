from odoo import models, api


class AccountFiscalPositionTax(models.Model):
    _name = 'account.fiscal.position.tax'
    _inherit = ['account.fiscal.position.tax', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('position_id', 'in', data['account.fiscal.position'].ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['account.fiscal.position']
