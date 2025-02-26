# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortalUruguay(CustomerPortal):

    def _is_uruguay_company(self):
        return request.env.company.country_code == 'UY'

    def _get_mandatory_fields(self):
        # EXTEND 'portal'
        mandatory_fields = super()._get_mandatory_fields()

        if self._is_uruguay_company():
            mandatory_fields.extend(('l10n_latam_identification_type_id', 'vat'))

        return mandatory_fields

    def _prepare_portal_layout_values(self):
        # EXTEND 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()

        if self._is_uruguay_company():
            partner = request.env.user.partner_id
            portal_layout_values.update({
                # Select CI identification type by default
                'identification': partner.l10n_latam_identification_type_id or request.env.ref('l10n_uy.it_ci').id,
                'identification_types': request.env['l10n_latam.identification.type'].search(
                    ['|', ('country_id', '=', False), ('country_id.code', '=', 'UY')]),
            })

        return portal_layout_values

    def details_form_validate(self, data, partner_creation=False):
        # EXTEND 'portal'
        error, error_message = super().details_form_validate(data, partner_creation)

        # sanitize identification value to make sure it's correctly written on the partner
        if self._is_uruguay_company() and data.get('l10n_latam_identification_type_id'):
            data['l10n_latam_identification_type_id'] = int(data['l10n_latam_identification_type_id'])

        return error, error_message
