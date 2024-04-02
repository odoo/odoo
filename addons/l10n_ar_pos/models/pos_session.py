# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if self.env.company.country_id.code == 'AR':
            data += ['l10n_ar.afip.responsibility.type', 'l10n_latam.identification.type']
        return data

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_id.code == 'AR':
            data['data'][0]['_consumidor_final_anonimo_id'] = self.env.ref('l10n_ar.par_cfa').id
        return data
