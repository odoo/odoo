# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_l10n_ph_void_counter = fields.Integer(
        related="pos_config_id.l10n_ph_void_counter",
        readonly=True,
    )
