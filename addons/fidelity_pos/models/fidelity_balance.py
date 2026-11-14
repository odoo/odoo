from odoo import api, models


class FidelityBalance(models.Model):
    _name = 'fidelity.balance'
    _inherit = ['fidelity.balance', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        card_ids = [c['id'] for c in data['fidelity.card']]
        return [('card_id', 'in', card_ids)]
