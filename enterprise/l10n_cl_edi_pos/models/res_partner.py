# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def get_sii_taxpayer_types(self):
        return self._fields['l10n_cl_sii_taxpayer_type']._description_selection(self.env)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        consumidor_final_anonimo = self.env.ref('l10n_cl.par_cfa').id

        for partner in self.ids:
            if partner == consumidor_final_anonimo:
                raise UserError(_('Deleting this partner is not allowed.'))

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'CL':
            result += ['l10n_latam_identification_type_id', 'l10n_cl_sii_taxpayer_type', 'l10n_cl_activity_description', 'l10n_cl_dte_email', 'street2']
        return result
