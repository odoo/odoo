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
