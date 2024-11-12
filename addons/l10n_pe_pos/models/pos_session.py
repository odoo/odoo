# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if self.env.company.country_id.code == "PE":
            data += ['l10n_pe.res.city.district', 'l10n_latam.identification.type', 'res.city']
        return data

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_id.code == "PE":
            data['data'][0]['_default_l10n_latam_identification_type_id'] = self.env.ref('l10n_pe.it_DNI').id
            data['data'][0]['_consumidor_final_anonimo_id'] = self.env.ref('l10n_pe_pos.partner_pe_cf').id
        return data
