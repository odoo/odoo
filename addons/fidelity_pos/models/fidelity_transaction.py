from odoo import api, models


class FidelityTransaction(models.Model):
    _name = 'fidelity.transaction'
    _inherit = ['fidelity.transaction', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return False
