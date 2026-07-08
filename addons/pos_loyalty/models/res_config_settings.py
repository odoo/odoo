from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'

    pos_loyalty_program_ids = fields.Many2many(
        'loyalty.program',
        related='pos_config_id.loyalty_program_ids',
        readonly=False,
    )
