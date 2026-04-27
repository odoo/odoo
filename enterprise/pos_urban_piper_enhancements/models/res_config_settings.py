from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_urbanpiper_minimum_preparation_time = fields.Integer(
        related='pos_config_id.urbanpiper_minimum_preparation_time',
        string='Minimum Preparation Time (Seconds)',
        help='The minimum amount of time the customer must wait for the order to be prepared.',
    )
