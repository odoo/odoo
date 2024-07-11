# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nPEWebsiteSale(WebsiteSale):

    def _get_mandatory_fields_billing(self, country_id=False):
        """Extend mandatory fields to add new identification, responsibility
        city_id and district fields when company is Peru"""
        res = super()._get_mandatory_fields_billing(country_id)
        if request.website.sudo().company_id.country_id.code != "PE":
            return res
        # For Peruvian company, the VAT is required for all the partners
        res.append("vat")
        if country_id == request.website.sudo().company_id.country_id.id:
            res += ["city_id", "l10n_pe_district", "l10n_latam_identification_type_id"]
            res.remove("city")
        return res

    def _get_mandatory_fields_shipping(self, country_id=False):
        """Extend mandatory fields to add city_id and district fields when the selected country is Peru"""
        res = super()._get_mandatory_fields_shipping(country_id)
        if request.website.sudo().company_id.country_id.code != "PE":
            return res
        if country_id == request.website.sudo().company_id.country_id.id:
            res += ["city_id", "l10n_pe_district"]
            res.remove("city")
        return res

    def _get_country_related_render_values(self, kw, render_values):
        res = super()._get_country_related_render_values(kw, render_values)

        if request.website.sudo().company_id.country_id.code == "PE":
            values = render_values["checkout"]
            state = "state_id" in values \
                    and values["state_id"] != "" \
                    and request.env["res.country.state"].browse(int(values["state_id"]))
            city = "city_id" in values \
                    and values["city_id"] != "" \
                    and request.env["res.city"].browse(int(values["city_id"]))
            to_include = {
                "identification": kw.get("l10n_latam_identification_type_id"),
                "identification_types": request.env["l10n_latam.identification.type"].sudo().search(
                    ["|", ("country_id", "=", False), ("country_id.code", "=", "PE")]
                ),
            }
            if state:
                to_include["state"] = state
                to_include["state_cities"] = request.env["res.city"].sudo().search([("state_id", "=", state.id)])
            if city:
                to_include["city"] = city
                to_include["city_districts"] = request.env["l10n_pe.res.city.district"].sudo().search([("city_id", "=", city.id)])
            res.update(to_include)
        return res

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        if request.website.sudo().company_id.account_fiscal_country_id.code == "PE":
            res.update({
                "l10n_latam_identification_type_id":
                    int(data["l10n_latam_identification_type_id"])
                    if data.get("l10n_latam_identification_type_id") else False,
                "name": data.get("name", False),
            })
        return res

    @http.route(
        ['/shop/state_infos/<model("res.country.state"):state>'],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def state_infos(self, state, **kw):
        states = request.env["res.city"].sudo().search([("state_id", "=", state.id)])
        return {'cities': [(c.id, c.name, c.l10n_pe_code) for c in states]}

    @http.route(
        ['/shop/city_infos/<model("res.city"):city>'], type="json", auth="public", methods=["POST"], website=True
    )
    def city_infos(self, city, **kw):
        districts = request.env["l10n_pe.res.city.district"].sudo().search([("city_id", "=", city.id)])
        return {'districts': [(d.id, d.name, d.code) for d in districts]}
