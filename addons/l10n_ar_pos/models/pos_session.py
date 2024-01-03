# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):

    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)

        if self.company_id.country_code == 'AR':
            params['res.partner']['fields'] += ['l10n_ar_afip_responsibility_type_id', 'l10n_latam_identification_type_id']
            params['l10n_ar.afip.responsibility.type'] = {'domain': [], 'fields': ['name']}
            params['l10n_latam.identification.type'] = {
                'domain': [('l10n_ar_afip_code', '!=', False), ('active', '=', True)],
                'fields': ['name']
            }

        return params

    def load_data(self, models_to_load, only_data=False):
        response = super().load_data(models_to_load, only_data)

        if not only_data:
            response['custom']['consumidor_final_anonimo_id'] = self.env.ref('l10n_ar.par_cfa').id

        return response
