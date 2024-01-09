# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nBRWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Extend mandatory fields to add the vat in case the website and the customer are from brazil"""
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)

        if (
            country_sudo.code == 'BR'
            and request.website.sudo().company_id.country_id.code == 'BR'
        ):
            mandatory_fields.add('vat')

        return mandatory_fields

    def _prepare_address_form_values(self, *args, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            *args, address_type=address_type, **kwargs
        )
        if address_type == 'billing' and request.website.sudo().company_id.country_id.code == 'BR':
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'BR'),
                ]) if can_edit_vat else LatamIdentificationType,
            })
        return rendering_values
