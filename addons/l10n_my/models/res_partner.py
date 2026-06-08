from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_is_company(self):
        super()._compute_is_company()
        for partner in self:
            if partner.country_code == 'MY' and partner.is_company and partner.vat.upper().startswith("IG"):
                partner.is_company = False
