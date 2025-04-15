# -*- coding: utf-8 -*-
from odoo import api, models


class PosSession(models.Model):

    _inherit = 'pos.session'

    @api.model
    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        if self.company_id.country_code == 'AR':
            res += ['l10n_ar.afip.responsibility.type', 'l10n_latam.identification.type']
        return res

    def _loader_params_res_partner(self):
        vals = super()._loader_params_res_partner()
        if self.company_id.country_code == 'AR':
            vals['search_params']['fields'] += ['l10n_ar_afip_responsibility_type_id', 'l10n_latam_identification_type_id']
        return vals

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if self.company_id.country_code == 'AR':
            loaded_data['consumidor_final_anonimo_id'] = self.env.ref('l10n_ar.par_cfa').id

    def _get_pos_ui_l10n_ar_afip_responsibility_type(self, params):
        return self.env['l10n_ar.afip.responsibility.type'].search_read(**params['search_params'])

    def _loader_params_l10n_ar_afip_responsibility_type(self):
        return {'search_params': {'domain': [], 'fields': ['name']}}

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        return self.env['l10n_latam.identification.type'].search_read(**params['search_params'])

    def _loader_params_l10n_latam_identification_type(self):
        """ filter only identification types used in Argentina"""
        return {
            'search_params': {
                'domain': [('l10n_ar_afip_code', '!=', False), ('active', '=', True)],
                'fields': ['name']},
        }
