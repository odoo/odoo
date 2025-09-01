from odoo import api, models
from odoo.addons.account.models.partner import _ref_company_registry


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # In Denmark, if you have a VAT number, it's also your company registry (CVR) number
        super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == 'DK' and p.vat):
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country in ('DK', '') and self._check_vat_number('DK', vat_number):
                partner.company_registry = vat_number

    @api.depends('country_id.code', 'ref_company_ids.account_fiscal_country_id.code')
    def _compute_company_registry_placeholder(self):
        super()._compute_company_registry_placeholder()
        for partner in self:
            country = partner.ref_company_ids[:1].account_fiscal_country_id or partner.country_id
            if country.code == 'DK':
                partner.company_registry_placeholder = _ref_company_registry.get('dk') or ''

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        labels['DK'] = 'CVR'
        return labels
