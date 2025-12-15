# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


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
                'can_edit_vat': partner.can_edit_vat(),
                'responsibility': partner.l10n_ar_afip_responsibility_type_id,
                'identification': partner.l10n_latam_identification_type_id,
                'partner_sudo': partner,
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
            identification_fields = [
                'l10n_latam_identification_type_id',
                'l10n_ar_afip_responsibility_type_id',
                'country_id',
            ]
            for identification_field in identification_fields:
                if data.get(identification_field):
                    data[identification_field] = int(data[identification_field])
                elif identification_field != 'country_id':
                    error[identification_field] = 'missing'
                    error_message.append(
                        request.env._("Some required fields are empty."),
                    )
            vat_fields = ['vat', 'name', *identification_fields]
            try:
                request.env['res.partner'].sudo().new({
                    fname: data[fname] for fname in vat_fields if fname in data
                }).with_context(no_vat_validation=True).check_vat()
            except ValidationError as exception:
                error['vat'] = 'error'
                error_message.extend(exception.args)
        return error, error_message
