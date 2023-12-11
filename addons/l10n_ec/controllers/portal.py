# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route


class CustomerPortalEcuador(CustomerPortal):

    OPTIONAL_BILLING_FIELDS = [*CustomerPortal.OPTIONAL_BILLING_FIELDS, "l10n_latam_identification_type_id"]

    def _is_ecuador_company(self):
        return request.env.company.country_code == 'EC'

    @route()
    def account(self, redirect=None, **post):
        # EXTEND 'portal'
        response = super().account(redirect=redirect, **post)

        if self._is_ecuador_company():
            if post and request.httprequest.method == 'POST':
                l10n_latam_identification_type_id = int(post.pop('l10n_latam_identification_type_id') or False) or False
                partner = request.env.user.partner_id
                post.update({'l10n_latam_identification_type_id': l10n_latam_identification_type_id})
                partner.sudo().write({'l10n_latam_identification_type_id': l10n_latam_identification_type_id})

            response.qcontext.update({
                'identification': post.get('l10n_latam_identification_type_id'),
                'identification_types': request.env['l10n_latam.identification.type'].search(
                    ['|', ('country_id', '=', False), ('country_id.code', '=', 'EC')]),
            })

        return response

    def details_form_validate(self, data, partner_creation=False):
        # EXTEND 'portal'
        error, error_message = super(CustomerPortalEcuador, self).details_form_validate(data)

        if self._is_ecuador_company():
            required_ecuador_fields = ("l10n_latam_identification_type_id", "vat")
            for field_name in required_ecuador_fields:
                if not data.get(field_name):
                    error[field_name] = 'missing'

        return error, error_message
