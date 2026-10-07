from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_is_company(self):
        super()._compute_is_company()
        for partner in self:
            if partner.country_code == 'MY' and partner.is_company and partner.vat.upper().startswith("IG"):
                partner.is_company = False

    def _l10n_my_get_registration_number(self):
        self.ensure_one()
        return self._get_additional_identifier('MY_EN')
