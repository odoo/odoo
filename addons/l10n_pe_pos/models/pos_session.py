# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        if self.env.company.country_id.code == "PE":
            data += ['l10n_pe.res.city.district', 'l10n_latam.identification.type', 'res.city']
        return data
