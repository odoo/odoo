# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nPEWebsiteSale(WebsiteSale):

    def _get_mandatory_fields_billing(self, country_id=False):
        """Extend mandatory fields to add new identification and responsibility fields when company is perú"""
        res = super()._get_mandatory_fields_billing(country_id)
        if request.website.sudo().company_id.country_id.code == "PE":
            res += ["l10n_latam_identification_type_id", "vat"]
        return res

    def _get_country_related_render_values(self, kw, render_values):
        res = super()._get_country_related_render_values(kw, render_values)
        if request.website.sudo().company_id.country_id.code == "PE":
            res.update({'identification': kw.get('l10n_latam_identification_type_id'),
                        'identification_types': request.env['l10n_latam.identification.type'].search(
                            ['|', ('country_id', '=', False), ('country_id.code', '=', 'PE')])})
        return res

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        if request.website.sudo().company_id.country_id.code == "PE":
            res.update({'l10n_latam_identification_type_id': int(data['l10n_latam_identification_type_id'])
                                                             if data.get('l10n_latam_identification_type_id') else False})
            res.update({'name': data['name'] if data.get('name') else False})
        return res
