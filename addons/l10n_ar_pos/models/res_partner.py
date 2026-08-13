# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.ondelete(at_uninstall=False)
    def _ar_unlink_except_master_data(self):
        consumidor_final_anonimo = self.env.ref('l10n_ar.par_cfa').id
        for partner in self.ids:
            if partner == consumidor_final_anonimo:
                raise UserError(_('Deleting this partner is not allowed.'))

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'AR':
            params += ['l10n_ar_afip_responsibility_type_id', 'l10n_latam_identification_type_id']
        return params
