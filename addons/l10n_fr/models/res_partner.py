import re

from odoo import api, fields, models
from odoo.tools import format_datetime


VAT_SIREN_RE = re.compile(r'FR[A-Z0-9]{2}([0-9]{9})', re.IGNORECASE)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

    def _l10n_fr_get_siren_from_vat(self):
        self.ensure_one()
        vat = (self.vat or '').replace(' ', '')
        match = VAT_SIREN_RE.fullmatch(vat)
        return match and match.group(1)

    @api.model
    def _get_supported_enrichment_types(self):
        return [*super()._get_supported_enrichment_types(), 'vat']

    @api.model
    def autocomplete_by_field(self, fieldName, query, query_country_id, timeout=15, include_branches=False):
        """SIREN and SIRET have no country prefix, including when entered in the name."""
        identifier = query.replace(' ', '')
        if fieldName.lower() in ('fr_siren', 'fr_siret') or (
            fieldName == 'name' and re.fullmatch(r'(?:[0-9]{9}|[0-9]{14})', identifier)
        ):
            return self.autocomplete_by_vat(identifier, self.env.ref('base.fr').id, timeout=timeout, include_branches=include_branches)
        return super().autocomplete_by_field(fieldName, query, query_country_id, timeout=timeout, include_branches=include_branches)

    @api.model
    def _process_enriched_response(self, response, error):
        result = super()._process_enriched_response(response, error)
        if response and (status := response.get('enrichment_status')) and status.get('inpi_stale'):
            if last_sync := status.get('inpi_last_sync'):
                result['warning'] = self.env._(
                    'Some company information was last retrieved from INPI on %s and may be outdated. Please verify the suggested values.',
                    format_datetime(self.env, last_sync),
                )
            else:
                result['warning'] = self.env._(
                    'Additional company information from INPI is unavailable. Some values may be missing. Please verify the suggested values.',
                )
        return result
