from odoo import models, api


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = ['account.fiscal.position', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        partner_fp_ids = data['res.partner'].fiscal_position_id.ids if data['res.partner'] else []
        return [('id', 'in', data['pos.config'].fiscal_position_ids.ids + data['pos.preset'].fiscal_position_id.ids + partner_fp_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'display_name', 'tax_map', 'tax_ids']
