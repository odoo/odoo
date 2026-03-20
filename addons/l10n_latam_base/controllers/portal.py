# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class L10nLatamBasePortalAccount(PortalAccount):

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if request.env.company._is_latam() and rendering_values['is_used_as_billing']:
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'identification_type': (
                    rendering_values['current_partner'].l10n_latam_identification_type_id
                    or self._l10n_get_default_identification_type_id()
                ),
                'identification_types': LatamIdentificationType.search([
                    '|',
                        ('country_id', '=', False),
                        ('country_id.code', '=', request.env.company.country_code),
                ]) if can_edit_vat else LatamIdentificationType,
                'vat_label': request.env._("Identification Number"),
                'is_latam_country': True,
                'display_b2b_fields': True,
            })
        return rendering_values

    def _get_mandatory_billing_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        if request.env.company._is_latam():
            mandatory_fields.update({'l10n_latam_identification_type_id', 'vat'})
        return mandatory_fields

    def _get_vat_validation_fields(self):
        fnames = super()._get_vat_validation_fields()
        if request.env.company._is_latam():
            fnames.update({'name', 'l10n_latam_identification_type_id'})
        return fnames

    def _l10n_get_default_identification_type_id(self):
        """Hook to set default identification type depending on LATAM country."""
        return request.env['l10n_latam.identification.type']
