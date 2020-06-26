# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route
from odoo.exceptions import ValidationError
from odoo import _


class L10nARCustomerPortal(CustomerPortal):

    OPTIONAL_BILLING_FIELDS = CustomerPortal.OPTIONAL_BILLING_FIELDS + [
        "l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id"]

    def is_argentinian_company(self, redirect=None, **post):
        return request.env.company.country_id == request.env.ref('base.ar')

    @route()
    def account(self, redirect=None, **post):
        """Extend in order to add information about the identification types and AFI responsibility show in portal"""
        if not self.is_argentinian_company():
            return super().account(redirect=redirect, **post)

        if post and request.httprequest.method == 'POST':
            post.update({'l10n_latam_identification_type_id': int(post.pop('l10n_latam_identification_type_id') or False) or False,
                         'l10n_ar_afip_responsibility_type_id': int(post.pop('l10n_ar_afip_responsibility_type_id') or False) or False})

        response = super().account(redirect=redirect, **post)
        response.qcontext.update({
            'identification_types': request.env['l10n_latam.identification.type'].sudo().search([]),
            'responsibility_types': request.env['l10n_ar.afip.responsibility.type'].sudo().search([]),
            'identification': post.get('l10n_latam_identification_type_id'),
            'responsibility': post.get('l10n_ar_afip_responsibility_type_id')})
        return response

    def _vat_validation(self, data, error, error_message):
        """ If Argentinian Company Do the vat validation taking into account the identification_type """
        if not self.is_argentinian_company():
            return super()._vat_validation(data, error, error_message)

        partner = request.env.user.partner_id
        if data.get("l10n_latam_identification_type_id") and data.get("vat") and partner and \
           (partner.l10n_latam_identification_type_id.id != data.get("l10n_latam_identification_type_id") or partner.vat != data.get("vat")):
            if partner.can_edit_vat():
                if hasattr(partner, "check_vat"):
                    partner_dummy = partner.new({
                        'vat': data['vat'], 'country_id': (int(data['country_id']) if data.get('country_id') else False),
                        'l10n_latam_identification_type_id': (int(data['l10n_latam_identification_type_id'])
                                                              if data.get('l10n_latam_identification_type_id') else False),
                    })
                    try:
                        partner_dummy.check_vat()
                    except ValidationError as exception:
                        error["vat"] = 'error'
                        error_message.append(exception.name)
            else:
                error_message.append(_('Changing Number and Identification type is not allowed once document(s) have been issued for your account. Please contact us directly for this operation.'))
        return error, error_message
