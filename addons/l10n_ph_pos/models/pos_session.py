# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config):
        return [
            *super()._load_pos_data_models(config),
            "l10n_ph.discount.privilege",
        ]
