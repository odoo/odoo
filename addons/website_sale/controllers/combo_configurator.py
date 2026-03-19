# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.tools.image import image_data_uri

from odoo.addons.sale.controllers.combo_configurator import SaleComboConfiguratorController
from odoo.addons.website.models import ir_http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleComboConfiguratorController(SaleComboConfiguratorController, WebsiteSale):
    @route(
        route="/website_sale/combo_configurator/get_data",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def website_sale_combo_configurator_get_data(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        request.update_context(display_default_code=False)  # Hide internal product reference
        return super().sale_combo_configurator_get_data(*args, **kwargs)

    @route(
        route="/website_sale/combo_configurator/get_price",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def website_sale_combo_configurator_get_price(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_combo_configurator_get_price(*args, **kwargs)

    def _get_combo_item_data(
        self, combo, combo_item, selected_combo_item, date, currency, pricelist, **kwargs
    ):
        data = super()._get_combo_item_data(
            combo, combo_item, selected_combo_item, date, currency, pricelist, **kwargs
        )
        # To sell a product type 'combo', one doesn't need to publish all combo choices. This causes
        # an issue when public users access the image of each choice via the /web/image route. To
        # bypass this access check, we send the raw image URL if the product is inaccessible to the
        # current user.
        if not combo_item.product_id.sudo(False).has_access("read") and (
            combo_item_image := combo_item.product_id.image_256
        ):
            data["product"]["image_src"] = image_data_uri(combo_item_image)

        if not data["extra_price"]:
            return data

        if pricelist:
            rule_id = pricelist._get_product_price_rule(combo_item.product_id, 1.0, date=date)[1]
            if rule_id:
                rule = request.env["product.pricelist.item"].sudo().browse(rule_id)
                discount_percentage = 0.0
                if rule.compute_price == "percentage":
                    discount_percentage = rule.percent_price
                elif rule.compute_price == "formula":
                    discount_percentage = rule.price_discount

                if discount_percentage > 0:
                    data["extra_price"] -= data["extra_price"] * (discount_percentage / 100.0)

        website = ir_http.get_request_website()
        if website and website.show_line_subtotals_tax_selection == "tax_included":
            taxes = combo_item.product_id.taxes_id._filter_taxes_by_company(request.env.company)
            if hasattr(request, "fiscal_position") and request.fiscal_position:
                taxes = request.fiscal_position.map_tax(taxes)
            if taxes:
                tax_res = taxes.compute_all(
                    data["extra_price"],
                    currency,
                    1,
                    combo_item.product_id,
                    request.env.user.partner_id,
                )
                data["extra_price"] = tax_res["total_included"]

        return data
