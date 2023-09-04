# -*- coding: utf-8 -*-
from odoo import api, models


class PosSession(models.Model):

    _inherit = 'pos.session'

    @api.model
    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        if self.company_id.country_code == 'PE':
            res += ['l10n_latam.identification.type']
        return res

    def _loader_params_res_partner(self):
        vals = super()._loader_params_res_partner()
        if self.company_id.country_code == 'PE':
            vals['search_params']['fields'] += ['l10n_latam_identification_type_id']
        return vals

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if self.company_id.country_code == 'PE':
            loaded_data['consumidor_final_id'] = self.env.ref('l10n_pe_pos.partner_pe_cf').id

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        return self.env['l10n_latam.identification.type'].search_read(**params['search_params'])

    def _loader_params_l10n_latam_identification_type(self):
        """filter only identification types used in Peru"""
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name']},
        }
