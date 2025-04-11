from odoo import _, api, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('vat', 'country_id')
    def _l10n_tr_onchange_vat(self):
        if self.country_id.code == 'TR' and self.vat:
            if self.is_company and len(self.vat) != 10:
                raise UserError(_("You need to fill in the 10-digit VKN in the Tax ID."))
            elif not self.is_company and len(self.vat) != 11:
                raise UserError(_("You need to fill in the 11-digit TCKN in the Tax ID."))
