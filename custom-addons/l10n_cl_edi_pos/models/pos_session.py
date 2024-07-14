# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.company_id.country_code == 'CL':
            result.append('l10n_latam.identification.type')
        return result

    def _loader_params_l10n_latam_identification_type(self):
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name'],
            },
        }

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        return self.env['l10n_latam.identification.type'].search_read(**params['search_params'])

    def _loader_params_res_partner(self):
        vals = super()._loader_params_res_partner()
        if self.company_id.country_code == 'CL':
            vals['search_params']['fields'] += ['l10n_latam_identification_type_id', 'l10n_cl_sii_taxpayer_type', 'l10n_cl_activity_description', 'l10n_cl_dte_email']
        return vals

    def _loader_params_res_company(self):
        vals = super()._loader_params_res_company()
        if self.company_id.country_code == 'CL':
            vals['search_params']['fields'] += ['l10n_cl_dte_resolution_number', 'l10n_cl_dte_resolution_date']
        return vals

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].append('is_card_payment')
        return result

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if self.company_id.country_code == 'CL':
            loaded_data['sii_taxpayer_types'] = self.env['res.partner'].get_sii_taxpayer_types()
            loaded_data['consumidor_final_anonimo_id'] = self.env.ref('l10n_cl.par_cfa').id
