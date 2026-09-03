from odoo import api, models


class FidelityReward(models.Model):
    _name = 'fidelity.reward'
    _inherit = ['fidelity.reward', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('program_id', 'in', config.get_available_fidelity_programs().ids)]
