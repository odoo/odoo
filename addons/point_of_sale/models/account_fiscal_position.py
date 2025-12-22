from odoo import models, api


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = ['account.fiscal.position', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['pos.config']['data'][0]['fiscal_position_ids'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'display_name', 'tax_map']

    def action_archive(self):
        configs = self.env['pos.config'].search([('default_fiscal_position_id', 'in', self.ids)])
        configs.default_fiscal_position_id = False
        return super().action_archive()
