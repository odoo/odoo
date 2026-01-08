# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nARWebsiteSale(WebsiteSale):

    def _get_mandatory_fields_billing(self, country_id=False):
        """Extend mandatory fields to add new identification and responsibility fields when company is argentina"""
        res = super()._get_mandatory_fields_billing(country_id)
        if request.website.sudo().company_id.country_id.code == "AR":
            res += ["l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id", "vat"]
        return res

    def _get_country_related_render_values(self, kw, render_values):
        res = super()._get_country_related_render_values(kw, render_values)
        if request.website.sudo().company_id.country_id.code == "AR":
            res.update({'identification': kw.get('l10n_latam_identification_type_id'),
                        'responsibility': kw.get('l10n_ar_afip_responsibility_type_id'),
                        'responsibility_types': request.env['l10n_ar.afip.responsibility.type'].search([]),
                        'identification_types': request.env['l10n_latam.identification.type'].search(
                            ['|', ('country_id', '=', False), ('country_id.code', '=', 'AR')])})
        return res

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        if request.website.sudo().company_id.country_id.code == "AR":
            res.update({'l10n_latam_identification_type_id': int(data['l10n_latam_identification_type_id'])
                                                             if data.get('l10n_latam_identification_type_id') else False})
            res.update({'name': data['name'] if data.get('name') else False})
        return res

    def checkout_form_validate(self, mode, all_form_values, data):
        """ We extend the method to add a new validation. If AFIP Resposibility is:

        * Final Consumer or Foreign Customer: then it can select any identification type.
        * Any other (Monotributista, RI, etc): should select always "CUIT" identification type"""
        error, error_message = super().checkout_form_validate(mode, all_form_values, data)

        # Identification type and AFIP Responsibility Combination
        if request.website.sudo().company_id.country_id.code == "AR":
            if mode[1] == 'billing':
                if error and any(field in error for field in ['l10n_latam_identification_type_id', 'l10n_ar_afip_responsibility_type_id']):
                    return error, error_message
                id_type_id = data.get("l10n_latam_identification_type_id")
                afip_resp_id = data.get("l10n_ar_afip_responsibility_type_id")

                id_type = request.env['l10n_latam.identification.type'].browse(id_type_id) if id_type_id else False
                afip_resp = request.env['l10n_ar.afip.responsibility.type'].browse(afip_resp_id) if afip_resp_id else False

                if not id_type or not afip_resp:
                    # Those two values were not provided and are not required, skip the validation
                    return error, error_message

                cuit_id_type = request.env.ref('l10n_ar.it_cuit')

                # Check if the AFIP responsibility is different from Final Consumer or Foreign Customer,
                # and if the identification type is different from CUIT
                if afip_resp.code not in ['5', '9'] and id_type != cuit_id_type:
                    error["l10n_latam_identification_type_id"] = 'error'
                    error_message.append(_('For the selected AFIP Responsibility you will need to set CUIT Identification Type'))

        return error, error_message
