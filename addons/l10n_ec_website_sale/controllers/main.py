# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nECWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        if request.website.sudo().company_id.country_id.code != 'EC':
            return mandatory_fields

        # For Peruvian company, the VAT is required for all the partners
        mandatory_fields.add('vat')
        mandatory_fields.add('l10n_latam_identification_type_id')
        return mandatory_fields

    def _prepare_address_form_values(self, *args, address_type, use_delivery_as_billing, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            *args,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            **kwargs,
        )
        if (
            (address_type == 'billing' or use_delivery_as_billing)
            and request.website.sudo().company_id.country_id.code == 'EC'
        ):
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'EC')
                ]) if can_edit_vat else LatamIdentificationType,
                'vat_label': request.env._("Identification Number"),
            })

        return rendering_values

    def _get_vat_validation_fields(self):
        fnames = super()._get_vat_validation_fields()
        if request.website.sudo().company_id.account_fiscal_country_id.code == 'EC':
            fnames.add('l10n_latam_identification_type_id')
            fnames.add('name')
        return fnames

    def _get_shop_payment_values(self, order, **kwargs):
        payment_values = super()._get_shop_payment_values(order, **kwargs)
        company = order.company_id
        # Do not show payment methods without l10n_ec_sri_payment_id.
        # Payment methods without this fields could cause issues since we require a l10n_ec_sri_payment_id to post a move.
        if company.account_fiscal_country_id.code == 'EC':
            payment_methods = payment_values['payment_methods_sudo'].filtered(lambda pm: bool(pm.l10n_ec_sri_payment_id))
            payment_values['payment_methods_sudo'] = payment_methods
        return payment_values
