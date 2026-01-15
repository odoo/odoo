# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        if self.env.company.country_id.code == 'AR':
            data += ['l10n_ar.afip.responsibility.type', 'l10n_latam.identification.type']
        return data
