from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # In Denmark, if you have a VAT number, it's also your company registry (CVR) number
        super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == 'DK' and p.vat):
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country.isnumeric():
                vat_country = 'dk'
                vat_number = partner.vat
            if vat_country == 'dk' and self.simple_vat_check(vat_country, vat_number):
                partner.company_registry = vat_number
