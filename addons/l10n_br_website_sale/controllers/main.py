# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _lt
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nBRWebsiteSale(WebsiteSale):

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_delivery_address_fields(country_sudo)
        if (
            country_sudo.code == 'BR'
            and request.website.sudo().company_id.account_fiscal_country_id.code == 'BR'
        ):
            mandatory_fields |= {
                'vat', 'l10n_latam_identification_type_id', 'street_name', 'street2', 'street_number', 'zip', 'city_id', 'state_id', 'country_id'
            }
            mandatory_fields -= {'street', 'city'}  # Brazil uses the base_extended_address fields added above

        return mandatory_fields

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Extend mandatory fields to add the vat in case the website and the customer are from brazil"""
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)

        if (
            country_sudo.code == 'BR'
            and request.website.sudo().company_id.account_fiscal_country_id.code == 'BR'
        ):
            mandatory_fields |= {
                'vat', 'l10n_latam_identification_type_id', 'street_name', 'street2', 'street_number', 'zip', 'city_id', 'state_id', 'country_id'
            }
            mandatory_fields -= {'street', 'city'}  # Brazil uses the base_extended_address fields added above

        return mandatory_fields

    def _prepare_address_form_values(self, order_sudo, partner_sudo, *args, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            order_sudo, partner_sudo, *args, address_type=address_type, **kwargs
        )
        if (kwargs.get('use_delivery_as_billing') and address_type == 'delivery' or address_type == 'billing') and request.website.sudo().company_id.account_fiscal_country_id.code == 'BR':
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'BR'),
                ]) if can_edit_vat else LatamIdentificationType,
            })
            rendering_values['city_sudo'] = partner_sudo.city_id
            rendering_values['cities_sudo'] = request.env['res.city'].sudo().search([('country_id.code', '=', 'BR')])
            rendering_values['vat_label'] = _lt('Number')
        return rendering_values
