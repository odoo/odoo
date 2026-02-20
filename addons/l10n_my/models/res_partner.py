from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_is_company(self):
        super()._compute_is_company()
        for partner in self:
            if partner.country_code == 'MY' and not partner._is_vat_void(partner.vat) and partner.vat.upper().startswith("IG"):
                partner.is_company = False
