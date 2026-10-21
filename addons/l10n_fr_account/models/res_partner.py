from odoo import api, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('country_id.code', 'ref_company_ids.account_fiscal_country_id.code')
    def _compute_company_registry_placeholder(self):
        super()._compute_company_registry_placeholder()
        for partner in self:
            country = partner.ref_company_ids[:1].account_fiscal_country_id or partner.country_id
            if country.code == 'FR':
                partner.company_registry_placeholder = _('SIRET Number')
            elif country.code == 'PF':
                partner.company_registry_placeholder = _('No. Tahiti') # PF adheres to French regulations

    def _get_peppol_endpoint_value(self, country_code, field, eas):
        endpoint = super()._get_peppol_endpoint_value(country_code, field, eas)
        if (
            not endpoint
            and country_code == 'FR'
            and field == 'peppol_endpoint'
            and not self.company_registry
        ):
            return self._l10n_fr_get_siren_from_vat()
        return endpoint
