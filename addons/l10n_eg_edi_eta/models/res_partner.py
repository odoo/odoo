from odoo import api, fields, models

from odoo.addons.l10n_eg_edi_eta.tools.partner_identifiers import (
    EG_ADDITIONAL_IDENTIFIERS_METADATA,
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_eg_building_no = fields.Char('Building No.')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_eg_building_no']

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **EG_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.depends('country_id', 'additional_identifiers')
    @api.depends_context('company')
    def _compute_available_additional_identifiers_metadata(self):
        # The Foreign ID identifies non-Egyptian individuals: only offer it on foreign partners of an Egyptian company.
        super()._compute_available_additional_identifiers_metadata()
        foreign_id_metadata = self._lazy_translate_additional_identifiers_metadata(EG_ADDITIONAL_IDENTIFIERS_METADATA['EG_FID'])
        is_eg_company = self.env.company.account_fiscal_country_id.code == 'EG'
        for partner in self:
            metadata = partner.available_additional_identifiers_metadata or {}
            if 'EG_FID' in (partner.additional_identifiers or {}) or (
                is_eg_company and partner.country_code and partner.country_code != 'EG'
            ):
                metadata['EG_FID'] = foreign_id_metadata
            else:
                metadata.pop('EG_FID', None)
            partner.available_additional_identifiers_metadata = metadata

    def _address_fields(self):
        return super()._address_fields() + ['l10n_eg_building_no']

    def _check_l10n_eg_missing_address_data(self, invoice=False, issuer=False):
        """Returns true if the partner has any address data missing"""
        fields = [self.street, self.city, self.country_id]
        if self.country_code == 'EG' and not self.l10n_eg_building_no:
            fields.append(self.l10n_eg_building_no)
        partner_type = self._l10n_eg_get_partner_tax_type(issuer=issuer)
        if partner_type != 'P' or (invoice and invoice.amount_total >= invoice.company_id._get_invoicing_threshold()):
            if partner_type == 'P':
                return all(self[field] for field in fields) and self._get_additional_identifier('EG_NIN')
            fields.append('vat')
        return any(not value for value in fields)

    def _l10n_eg_get_partner_tax_type(self, issuer=False):
        if issuer:
            return 'B'
        if self.commercial_partner_id.country_code == 'EG':
            return 'B' if self.commercial_partner_id.is_company else 'P'
        return 'F'
