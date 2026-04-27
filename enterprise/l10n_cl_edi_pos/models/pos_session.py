# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_id.code == 'CL':
            data['data'][0]['_sii_taxpayer_types'] = self.env['res.partner'].get_sii_taxpayer_types()
            data['data'][0]['_consumidor_final_anonimo_id'] = self.env.ref('l10n_cl.par_cfa').id
            data['data'][0]['_l10n_cl_sii_regional_office_selection'] = dict(self.env.company._fields['l10n_cl_sii_regional_office'].selection)
        return data

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if self.env.company.country_id.code == 'CL':
            data += ['l10n_latam.identification.type', 'l10n_latam.document.type', 'account.move']
        return data
