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
        if invoice and invoice._l10n_eg_edi_is_receiver_exempt():
            return False
        fields = [self.street, self.city, self.country_id]
        if invoice and not self.commercial_partner_id.vat:
            # ETA requires the name and full address of an individual buyer above the invoicing threshold
            fields += [self.name or self.commercial_partner_id.name, self.state_id, self.l10n_eg_building_no]
        elif self.country_code == 'EG' and not self.l10n_eg_building_no:
            fields.append(self.l10n_eg_building_no)
        return any(not value for value in fields)

    def _l10n_eg_get_partner_identifier(self, issuer=False):
        """Return the receiver id ETA expects: the National ID of an individual, the VAT otherwise."""
        if self._l10n_eg_get_partner_tax_type(issuer=issuer) == 'P':
            # The National ID belongs to the person and is not synced to their child addresses
            return (
                self._get_additional_identifier('EG_NIN')
                or self.commercial_partner_id._get_additional_identifier('EG_NIN')
            )
        # Foreign individuals have no dedicated identifier yet: they fall back on the VAT
        return self.commercial_partner_id.vat

    def _l10n_eg_get_partner_tax_type(self, issuer=False):
        if issuer:
            return 'B'
        country_code = self.commercial_partner_id.country_code
        if not country_code or country_code == 'EG':
            return 'B' if self.commercial_partner_id.vat else 'P'
        return 'F'
