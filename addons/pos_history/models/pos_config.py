# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_history_tracked = fields.Boolean(
        string='Track History',
        help='Whether to track order history for this POS configuration',
        copy=False,
    )
