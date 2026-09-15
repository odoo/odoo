# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_ph_void_counter = fields.Integer(
        string="Void Counter",
        copy=False,
        help="Number of line void transactions for this POS configuration.",
    )

    @api.depends("l10n_ph_void_counter")
    def _compute_local_data_integrity(self):
        return super()._compute_local_data_integrity()
