# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nUYWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """ Extend mandatory fields to add new identification and responsibility fields when company is Uruguay. """
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        if request.website.sudo().company_id.country_id.code == 'UY':
            mandatory_fields |= {'l10n_latam_identification_type_id', 'vat'}
        return mandatory_fields

    def _prepare_address_form_values(self, order_sudo, partner_sudo, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            order_sudo, partner_sudo, address_type=address_type, **kwargs
        )
        if request.website.sudo().company_id.country_id.code != 'UY':
            return rendering_values

        if kwargs.get('use_delivery_as_billing') and address_type == 'delivery' or address_type == 'billing':
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'identification': partner_sudo.l10n_latam_identification_type_id or request.env.ref('l10n_uy.it_ci').id,
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'UY')
                ]) if can_edit_vat else LatamIdentificationType,
                'vat_label': request.env._("Identification Number"),
            })

        return rendering_values

    def _get_vat_validation_fields(self):
        fnames = super()._get_vat_validation_fields()
        if request.website.sudo().company_id.account_fiscal_country_id.code == 'UY':
            fnames.add('l10n_latam_identification_type_id')
            fnames.add('name')
        return fnames
