# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class L10nARCustomerPortal(CustomerPortal):

    def _is_argentine_company(self):
        return request.env.company.country_code == 'AR'

    def _get_optional_fields(self):
        # EXTEND 'portal'
        optional_fields = super()._get_optional_fields()

        if self._is_argentine_company():
            optional_fields.extend(('l10n_latam_identification_type_id', 'l10n_ar_afip_responsibility_type_id', 'vat'))

        return optional_fields

    def _prepare_portal_layout_values(self):
        # EXTEND 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()

        if self._is_argentine_company():
            partner = request.env.user.partner_id
            portal_layout_values.update({
                'responsibility': partner.l10n_ar_afip_responsibility_type_id,
                'identification': partner.l10n_latam_identification_type_id,
                'responsibility_types': request.env['l10n_ar.afip.responsibility.type'].search([]),
                'identification_types': request.env['l10n_latam.identification.type'].search(
                    ['|', ('country_id', '=', False), ('country_id.code', '=', 'AR')]),
            })

        return portal_layout_values

    def details_form_validate(self, data, partner_creation=False):
        # EXTEND 'portal'
        error, error_message = super().details_form_validate(data, partner_creation)

        # sanitize identification values to make sure it's correctly written on the partner
        if self._is_argentine_company():
            for identification_field in ('l10n_latam_identification_type_id', 'l10n_ar_afip_responsibility_type_id'):
                if data.get(identification_field):
                    data[identification_field] = int(data[identification_field])

        return error, error_message
