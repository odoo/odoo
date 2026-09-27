from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_eg_building_no = fields.Char('Building No.')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_eg_building_no']

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
