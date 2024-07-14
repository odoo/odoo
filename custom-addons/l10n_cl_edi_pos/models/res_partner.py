# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def get_sii_taxpayer_types(self):
        return self._sii_taxpayer_types

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        consumidor_final_anonimo = self.env.ref('l10n_cl.par_cfa').id

        for partner in self.ids:
            if partner == consumidor_final_anonimo:
                raise UserError(_('Deleting this partner is not allowed.'))
