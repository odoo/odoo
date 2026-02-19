from odoo import api, models


class FidelityCard(models.Model):
    _name = 'fidelity.card'
    _inherit = ['fidelity.card', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        partner_ids = [p['id'] for p in data['res.partner']]
        return [('partner_id', 'in', partner_ids)]
