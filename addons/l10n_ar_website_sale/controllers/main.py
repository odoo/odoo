# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request, route
from odoo.exceptions import ValidationError


class L10nARWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_fields(self):
        """Extend mandatory fields to add new identification and responsibility fields when company is argentina"""
        res = super()._get_mandatory_billing_fields()
        if request.website.sudo().company_id.country_id == request.env.ref('base.ar'):
            res += ["l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id", "vat"]
        return res

    @route()
    def address(self, **kw):
        """Extend to send information about the identification types and AFIP responsibility to show in the address form"""
        response = super().address(**kw)
        if request.website.sudo().company_id.country_id == request.env.ref('base.ar'):
            response.qcontext.update({'identification_types': request.env['l10n_latam.identification.type'].sudo().search([]),
                                      'responsibility_types': request.env['l10n_ar.afip.responsibility.type'].sudo().search([]),
                                      'identification': kw.get('l10n_latam_identification_type_id'),
                                      'responsibility': kw.get('l10n_ar_afip_responsibility_type_id')})
        return response

    def _vat_validation(self, data, error, error_message):
        """ Do the vat validation taking into account the identification_type """
        if request.website.sudo().company_id.country_id == request.env.ref('base.ar'):
            Partner = request.env['res.partner']
            if data.get("vat") and hasattr(Partner, "check_vat"):
                partner_dummy = Partner.new({
                    'vat': data['vat'],
                    'country_id': (int(data['country_id']) if data.get('country_id') else False),
                    'l10n_latam_identification_type_id': (int(data['l10n_latam_identification_type_id'])
                                                          if data.get('l10n_latam_identification_type_id') else False),
                })
                try:
                    partner_dummy.check_vat()
                except ValidationError as exception:
                    error["vat"] = 'error'
                    error_message.append(exception.name)
            return error, error_message
        return super()._vat_validation(data, error, error_message)
