# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class L10nARPortalAccount(CustomerPortal):

    def _is_argentinean_company(self):
        return request.env.company.country_code == 'AR'

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if self._is_argentinean_company() and rendering_values['is_used_as_billing']:
            can_edit_vat = rendering_values['can_edit_vat']
            ArAfipResponsibilityType = request.env['l10n_ar.afip.responsibility.type']
            rendering_values.update({
                'responsibility': rendering_values['current_partner'].l10n_ar_afip_responsibility_type_id,
                'responsibility_types': ArAfipResponsibilityType.search([]) if can_edit_vat else ArAfipResponsibilityType,
            })
        return rendering_values

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        """ We extend the method to add a new validation. If ARCA Resposibility is:

        * Final Consumer or Foreign Customer: then it can select any identification type.
        * Any other (Monotributista, RI, etc): should select always "CUIT" identification type
        """
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, *args, **kwargs
        )

        if address_type == 'billing' and self._is_argentinean_company():
            if 'l10n_ar_afip_responsibility_type_id' in missing_fields:
                return invalid_fields, missing_fields, error_messages

            afip_resp = request.env['l10n_ar.afip.responsibility.type'].browse(
                address_values.get('l10n_ar_afip_responsibility_type_id')
            )
            if not afip_resp or afip_resp.code in ['5', '9']:
                return invalid_fields, missing_fields, error_messages

            country = request.env['res.country'].browse(address_values.get('country_id'))
            if country.code != 'AR' or not address_values.get('vat'):
                invalid_fields.add('vat')
                error_messages.append(request.env._(
                    "For the selected ARCA Responsibility you must set a CUIT (country Argentina with VAT)."
                ))

        return invalid_fields, missing_fields, error_messages
