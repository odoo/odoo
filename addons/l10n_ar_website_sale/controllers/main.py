# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nARWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Extend mandatory fields to add new identification and responsibility fields when company is argentina"""
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        if request.website.sudo().company_id.country_id.code == 'AR':
            mandatory_fields |= {
                'l10n_latam_identification_type_id',
                'l10n_ar_afip_responsibility_type_id',
                'vat',
            }
        return mandatory_fields

    def _prepare_address_form_values(self, *args, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            *args, address_type=address_type, **kwargs
        )
        if (kwargs.get('use_delivery_as_billing') and address_type == 'delivery' or address_type == 'billing') and request.website.sudo().company_id.account_fiscal_country_id.code == 'AR':
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'responsibility_types': request.env['l10n_ar.afip.responsibility.type'].search([]),
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'AR'),
                ]) if can_edit_vat else LatamIdentificationType,
                'vat_label': request.env._("Number"),
            })
        return rendering_values

    def _get_vat_validation_fields(self):
        fnames = super()._get_vat_validation_fields()
        if request.website.sudo().company_id.country_id.code == "AR":
            fnames.add('name')
            fnames.add('l10n_latam_identification_type_id')
        return fnames

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        """ We extend the method to add a new validation. If AFIP Resposibility is:

        * Final Consumer or Foreign Customer: then it can select any identification type.
        * Any other (Monotributista, RI, etc): should select always "CUIT" identification type
        """
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, *args, **kwargs
        )

        # Identification type and AFIP Responsibility Combination
        if address_type == 'billing' and request.website.sudo().company_id.country_id.code == 'AR':
            if missing_fields and any(
                fname in missing_fields
                for fname in [
                    'l10n_latam_identification_type_id', 'l10n_ar_afip_responsibility_type_id'
                ]
            ):
                return invalid_fields, missing_fields, error_messages

            afip_resp = request.env['l10n_ar.afip.responsibility.type'].browse(
                address_values.get('l10n_ar_afip_responsibility_type_id')
            )
            id_type = request.env['l10n_latam.identification.type'].browse(
                address_values.get('l10n_latam_identification_type_id')
            )

            if not id_type or not afip_resp:
                # Those two values were not provided and are not required, skip the validation
                return invalid_fields, missing_fields, error_messages

            # Check if the AFIP responsibility is different from Final Consumer or Foreign Customer,
            # and if the identification type is different from CUIT
            if afip_resp.code not in ['5', '9'] and id_type != request.env.ref('l10n_ar.it_cuit'):
                invalid_fields.add('l10n_latam_identification_type_id')
                error_messages.append(request.env._(
                    "For the selected AFIP Responsibility you will need to set CUIT Identification Type"))

        return invalid_fields, missing_fields, error_messages
