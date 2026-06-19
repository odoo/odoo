# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.exceptions import ValidationError
from odoo.http import request, route

from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.website.controllers import main
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website_sale.models.website import (
    FISCAL_POSITION_SESSION_CACHE_KEY,
    PRICELIST_SELECTED_SESSION_CACHE_KEY,
    PRICELIST_SESSION_CACHE_KEY,
)


class WebsiteSaleForm(WebsiteForm):
    @route(
        "/website/form/shop.sale.order", type="http", auth="public", methods=["POST"], website=True
    )
    def website_form_saleorder(self, **kwargs):
        model_record = self.env.ref("sale.model_sale_order").sudo()
        try:
            data = self.extract_data(model_record, kwargs)
        except ValidationError as e:
            return json.dumps({"error_fields": e.args[0]})

        if not (order_sudo := request.cart):
            return json.dumps({"error": "No order found; please add a product to your cart."})

        if data["record"]:
            order_sudo.write(data["record"])

        if data["custom"]:
            order_sudo._message_log(body=nl2br_enclose(data["custom"], "p"), message_type="comment")

        if data["attachments"]:
            self.insert_attachment(model_record, order_sudo.id, data["attachments"])

        return json.dumps({"id": order_sudo.id})

    def extract_data(self, model_sudo, values):
        parent_name = values.pop("parent_name", None)
        data = super().extract_data(model_sudo, values)
        if model_sudo.model == "res.partner" and parent_name:
            # `parent_name` is a non-stored field, passing it in the record
            # allows to create the parent company during record creation.
            data["record"]["parent_name"] = parent_name
        return data


class Website(main.Website):
    def _login_redirect(self, uid, redirect=None):
        # If we are logging in, clear the current pricelist to be able to find
        # the pricelist that corresponds to the user afterwards.
        request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
        request.session.pop(FISCAL_POSITION_SESSION_CACHE_KEY, None)
        request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)
        return super()._login_redirect(uid, redirect=redirect)

    @route()
    def autocomplete(
        self,
        search_type=None,
        term=None,
        order=None,
        offset=0,
        limit=5,
        max_nb_chars=999,
        options=None,
    ):
        options = options or {}
        if "display_currency" not in options:
            options["display_currency"] = self.env.website.currency_id
        return super().autocomplete(search_type, term, order, offset, limit, max_nb_chars, options)

    @route()
    def get_current_currency(self, **_kwargs):
        return {
            "id": self.env.website.currency_id.id,
            "symbol": self.env.website.currency_id.symbol,
            "position": self.env.website.currency_id.position,
        }

    @route()
    def change_lang(self, lang, **kwargs):
        if cart := request.cart:
            self.env.add_to_compute(
                cart.order_line._fields["name"], cart.order_line.with_context(lang=lang)
            )
        return super().change_lang(lang, **kwargs)

    @route(
        "/shop/selectable_pricelists",
        type="http",
        methods=["GET"],
        auth="public",
        readonly=True,
        sitemap=False,
        website=True,
    )
    def get_selectable_pricelists(self):
        website = self.env.website
        selectable_pricelists = website.get_pricelist_available(show_visible=True)
        all_countries = self.env["res.country"].browse(self.env["res.country"]._cached_data()["id"])

        response = {
            "default_currency_id": website.company_id.currency_id.id,
            "currencies": {
                data["id"]: data
                for data in selectable_pricelists.currency_id.web_read({"name": {}, "symbol": {}})
            },
            "countries": {
                data["id"]: data
                for data in all_countries.web_read({"name": {}, "image_url": {}, "currency_id": {}})
            },
        }

        for currency, pricelists in selectable_pricelists.grouped("currency_id").items():
            response["currencies"][currency.id]["pricelist_id"] = pricelists[:1].id

        if request.env.user._is_internal():
            # Ensure the internal users can always see the most up to date list of pricelists.
            cache_control = "no-cache"
        else:
            # Cache the pricelists for public/portal users for 7 days.
            cache_control = "public, max-age=604800, stale-while-revalidate=86400"

        return request.make_json_response(response, headers=[("Cache-Control", cache_control)])
