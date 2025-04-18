# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class L10nESPortalAccount(PortalAccount):

    def _prepare_address_form_values(self, *args, **kwargs):
        """Ensure B2B fields are always displayed on Spanish e-commerce."""
        rendering_values = super()._prepare_address_form_values(*args, **kwargs)
        if not rendering_values.get('display_b2b_fields'):
            rendering_values['display_b2b_fields'] = request.env.company.country_code == 'ES'
        return rendering_values

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Require VAT/NIF for Spanish customers in billing addresses on Spanish e-commerce."""
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)

        if request.env.company.country_code == country_sudo.code == 'ES':
            field_names.add('vat')

        return field_names

    def _get_mandatory_address_fields(self, country_sudo):
        """Require State for Spanish customers on Spanish e-commerce."""
        field_names = super()._get_mandatory_address_fields(country_sudo)

        if request.env.company.country_code == country_sudo.code == 'ES':
            field_names.add('state_id')

        return field_names

    def _complete_address_values(self, address_values, *args, **kwargs):
        super()._complete_address_values(address_values, *args, **kwargs)
        vat_without_country_code = address_values.get('vat', '')[2:]
        address_values.update({
            'is_company': vat_without_country_code and not vat_without_country_code[0].isdigit() and vat_without_country_code[0] not in ('X', 'Y', 'Z'),
        })
