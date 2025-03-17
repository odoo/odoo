from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nESWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Require VAT/NIF for Spanish customers in billing addresses on Spanish e-commerce."""
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)

        if request.website.sudo().company_id.country_code == country_sudo.code == 'ES':
            field_names |= {'vat'}

        return field_names

    def _get_mandatory_address_fields(self, country_sudo):
        """Require State for Spanish customers on Spanish e-commerce."""
        field_names = super()._get_mandatory_address_fields(country_sudo)

        if request.website.sudo().company_id.country_code == country_sudo.code == 'ES':
            field_names |= {'state_id'}

        return field_names

    def _complete_address_values(self, address_values, address_type, use_same, order_sudo):
        super()._complete_address_values(address_values, address_type, use_same, order_sudo)
        vat_without_country_code = address_values.get('vat', '')[2:]
        address_values.update({
            'is_company': vat_without_country_code and not vat_without_country_code[0].isdigit() and vat_without_country_code[0] not in ('X', 'Y', 'Z'),
        })
