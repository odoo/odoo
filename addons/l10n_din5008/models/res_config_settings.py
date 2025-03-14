from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    has_position_column = fields.Boolean(
        related='company_id.has_position_column',
        readonly=False,
    )
