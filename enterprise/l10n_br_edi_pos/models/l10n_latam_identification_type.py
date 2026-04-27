# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class L10nLatamIdentificationType(models.Model):
    _name = "l10n_latam.identification.type"
    _inherit = ["l10n_latam.identification.type", "pos.load.mixin"]

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Makes the POS load this model."""
        res = super()._load_pos_data_fields(config_id)
        if self.env["pos.config"].browse(config_id).l10n_br_is_nfce:
            res += ["name"]
        return res
