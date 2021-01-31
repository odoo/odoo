# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

from odoo.addons.website_sale.controllers.main import WebsiteSale as Base


class WebsiteSale(Base):
    @http.route("/shop/products/slider", type="json", auth="public", website=True)
    def products_slider(self, list_id=0, **kwargs):
        return self._get_products_slider(list_id)

    def _get_products_slider(self, list_id):
        """
        Returns list of  products according to snippet settings
        """
        max_number_of_product_for_carousel = 12
        product_list = request.env["product.list"].sudo().browse(list_id)
        if not product_list:
            return {}

        domain = safe_eval(product_list.products_domain)
        Product = request.env["product.product"].with_context(display_default_code=False)
        products_ids = Product.search(domain, limit=min(max_number_of_product_for_carousel, product_list.limit))

        FieldMonetary = request.env["ir.qweb.field.monetary"]
        monetary_options = {
            "display_currency": request.website.get_current_pricelist().currency_id,
        }
        rating = request.website.viewref("website_sale.product_comment").active
        res = {"products": []}
        for product in products_ids:
            combination_info = product._get_combination_info_variant()
            res_product = product.read(["id", "name", "website_url"])[0]
            res_product.update(combination_info)
            res_product["price"] = FieldMonetary.value_to_html(res_product["price"], monetary_options)
            if rating:
                res_product["rating"] = request.env["ir.ui.view"].render_template(
                    "website_rating.rating_widget_stars_static",
                    values={"rating_avg": product.rating_avg, "rating_count": product.rating_count},
                )
            res["products"].append(res_product)

        return res
