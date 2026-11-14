from odoo import api, fields, models


class FidelityProgram(models.Model):
    _name = 'fidelity.program'
    _inherit = ['fidelity.program', 'pos.load.mixin']

    available_in_pos = fields.Boolean(
        string="Available in PoS",
        default=True,
        help="Indicates whether this fidelity program is available in the Point of Sale.",
    )
    pos_config_ids = fields.Many2many(
        'pos.config',
        store=True,
        readonly=False,
        string="Point of Sales",
        help="Restrict publishing to those shops.",
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', config.get_available_fidelity_programs().ids)]
