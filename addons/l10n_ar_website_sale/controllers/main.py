# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request, route


class L10nARWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_fields(self):
        """Extend mandatory fields to add new identification and responsibility fields when company is argentina"""
        res = super()._get_mandatory_billing_fields()
        if request.website.sudo().company_id.country_id.code == "AR":
            res += ["l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id", "vat"]
        return res

    @route()
    def address(self, **kw):
        """Extend to send information about the identification types and AFIP responsibility to show in the address form"""
        response = super().address(**kw)
        if request.website.sudo().company_id.country_id.code == "AR":
            response.qcontext.update({'identification_types': request.env['l10n_latam.identification.type'].search(['|', ('country_id', '=', False), ('country_id.code', '=', 'AR')]),
                                      'responsibility_types': request.env['l10n_ar.afip.responsibility.type'].search([]),
                                      'identification': kw.get('l10n_latam_identification_type_id'),
                                      'responsibility': kw.get('l10n_ar_afip_responsibility_type_id')})
        return response

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        if request.website.sudo().company_id.country_id.code == "AR":
            res.update({'l10n_latam_identification_type_id': int(data['l10n_latam_identification_type_id'])
                                                             if data.get('l10n_latam_identification_type_id') else False})
        return res

    def checkout_form_validate(self, mode, all_form_values, data):
        """ We extend the method to add a new validation. If AFIP Resposibility is:

        * Final Consumer or Foreign Customer: then it can select any identification type.
        * Any other (Monotributista, RI, etc): should select always "CUIT" identification type"""
        error, error_message = super().checkout_form_validate(mode, all_form_values, data)

        if mode[1] == 'billing':
            # Identification type and AFIP Responsibility Combination
            id_type_id = data.get("l10n_latam_identification_type_id")
            afip_resp_id = data.get("l10n_ar_afip_responsibility_type_id")

            id_type = request.env['l10n_latam.identification.type'].browse(id_type_id) if id_type_id else False
            afip_resp = request.env['l10n_ar.afip.responsibility.type'].browse(afip_resp_id) if afip_resp_id else False

            final_consumer = request.env.ref('l10n_ar.res_CF')
            foreign_customer = request.env.ref('l10n_ar.res_EXT')
            cuit_id_type = request.env.ref('l10n_ar.it_cuit')

            if afip_resp != final_consumer and afip_resp != foreign_customer and id_type != cuit_id_type:
                error["l10n_latam_identification_type_id"] = 'error'
                error_message.append(_('For the selected AFIP Responsibility you will need to set CUIT Identification Type'))

        return error, error_message
