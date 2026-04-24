# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_history_tracked = fields.Boolean(string='Track History', related='pos_config_id.is_history_tracked',
        readonly=False, help='Whether to track order history for this POS configuration.')
