# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nESWebsiteSale(WebsiteSale):

    def _validate_address_values(self, address_values, partner_sudo, address_type, use_delivery_as_billing, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, use_delivery_as_billing, *args, **kwargs
        )

        return invalid_fields, missing_fields, error_messages

    def _get_mandatory_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_address_fields(country_sudo)

        if self.env.company.country_code == country_sudo.code == 'ES':
            field_names.update(('vat', 'state_id'))

        return field_names

    def _update_partner(self, partner):
        super()._update_partner(partner)

        if partner.vat and not partner.vat[0].isdigit() and partner.vat[0] not in ('L', 'K'):
            partner.write({
                'company_type': 'company',
            })

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)

        if self.env.company.country_code == 'ES' and 'vat' in address_values:
            address_values['vat'] = address_values['vat'][2:]

        return address_values, extra_form_data

    def _get_vat_validation_fields(self):
        if self.env.company.country_code == 'ES':
            return {'vat'}

        return super()._get_vat_validation_fields()
