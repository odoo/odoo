from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route


class CustomerPortalAr(CustomerPortal):

    OPTIONAL_BILLING_FIELDS = [*CustomerPortal.OPTIONAL_BILLING_FIELDS, "l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id"]

    def is_argentinian_company(self):
        return request.env.company.country_code == 'AR'

    @route()
    def account(self, redirect=None, **post):
        """Extend in order to add information about the identification types and AFIP responsibility show in portal"""
        response = super().account(redirect=redirect, **post)

        if self.is_argentinian_company():
            if post and request.httprequest.method == 'POST':
                l10n_latam_identification_type_id = int(post.pop('l10n_latam_identification_type_id') or False) or False
                l10n_ar_afip_responsibility_type_id = int(post.pop('l10n_ar_afip_responsibility_type_id') or False) or False

                partner = request.env.user.partner_id
                post.update({
                    'l10n_latam_identification_type_id': l10n_latam_identification_type_id,
                    'l10n_ar_afip_responsibility_type_id': l10n_ar_afip_responsibility_type_id,
                })
                partner.sudo().write({
                    'l10n_latam_identification_type_id': l10n_latam_identification_type_id,
                    'l10n_ar_afip_responsibility_type_id': l10n_ar_afip_responsibility_type_id,
                })

            response.qcontext['identification'] = post.get('l10n_latam_identification_type_id')
            response.qcontext['identification_types'] = request.env['l10n_latam.identification.type'].search(
                    [('l10n_ar_afip_code', '!=', False)])
            response.qcontext['responsibility'] = post.get('l10n_ar_afip_responsibility_type_id')
            response.qcontext['responsibility_types'] = request.env['l10n_ar.afip.responsibility.type'].sudo().search([])
        return response

    def details_form_validate(self, data, partner_creation=False):
        # EXTEND 'portal'
        error, error_message = super(CustomerPortalAr, self).details_form_validate(data)

        if self.is_argentinian_company():
            required_ar_fields = ("l10n_latam_identification_type_id", "vat", "l10n_ar_afip_responsibility_type_id")
            for field_name in required_ar_fields:
                if not data.get(field_name):
                    error[field_name] = 'missing'

        return error, error_message
