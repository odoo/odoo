# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nPEWebsiteSale(WebsiteSale):
    def _get_mandatory_fields_billing(self, country_id=False):
        """Extend mandatory fields to add new identification and responsibility fields when company is Peru"""
        res = super()._get_mandatory_fields_billing(country_id)
        if request.website.sudo().company_id.country_id.code == "PE":
            res += ["l10n_latam_identification_type_id", "vat"]
        return res

    def _get_country_related_render_values(self, kw, render_values):
        res = super()._get_country_related_render_values(kw, render_values)

        if request.website.sudo().company_id.country_id.code == "PE":
            values = render_values["checkout"]
            state = (
                "state_id" in values
                and values["state_id"] != ""
                and request.env["res.country.state"].browse(int(values["state_id"]))
            )
            city = (
                "city_id" in values
                and values["city_id"] != ""
                and request.env["res.city"].browse(int(values["city_id"]))
            )
            to_include = {
                "identification": kw.get("l10n_latam_identification_type_id"),
                "identification_types": request.env["l10n_latam.identification.type"].search(
                    ["|", ("country_id", "=", False), ("country_id.code", "=", "PE")]
                ),
            }
            if state:
                to_include["state"] = state
                to_include["state_cities"] = state.get_website_sale_cities()
            if city:
                to_include["city"] = city
                to_include["city_districts"] = city.get_website_sale_districts()
            res.update(to_include)
        return res

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        if request.website.sudo().company_id.country_id.code == "PE":
            res.update(
                {
                    "l10n_latam_identification_type_id": int(data["l10n_latam_identification_type_id"])
                    if data.get("l10n_latam_identification_type_id")
                    else False
                }
            )
            res.update({"name": data["name"] if data.get("name") else False})
        return res

    @http.route(
        ['/shop/state_infos/<model("res.country.state"):state>'],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def state_infos(self, state, mode, **kw):
        return dict(
            cities=[(c.id, c.name, c.l10n_pe_code) for c in state.get_website_sale_cities(mode=mode)],
        )

    @http.route(
        ['/shop/city_infos/<model("res.city"):city>'], type="json", auth="public", methods=["POST"], website=True
    )
    def city_infos(self, city, mode, **kw):
        return dict(
            districts=[(d.id, d.name, d.code) for d in city.get_website_sale_districts(mode=mode)],
        )
