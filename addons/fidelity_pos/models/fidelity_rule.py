from odoo import api, models


class FidelityRule(models.Model):
    _name = 'fidelity.rule'
    _inherit = ['fidelity.rule', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('program_id', 'in', config.get_available_fidelity_programs().ids)]
