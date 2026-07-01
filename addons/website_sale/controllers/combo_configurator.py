# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.tools.image import image_data_uri

from odoo.addons.sale.controllers.combo_configurator import SaleComboConfiguratorController
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

        product_tmpl_id = kwargs.get("product_tmpl_id")
        quantity = kwargs.get("quantity")
        date = kwargs.get("date")
        pricelist = kwargs.get("pricelist")

        if pricelist and product_tmpl_id:
            product_tmpl = self.env["product.template"].browse(product_tmpl_id)
            rule_id = pricelist._get_product_price_rule(product_tmpl, quantity, date=date)[1]
            if rule_id:
                kwargs["combo_rule_id"] = rule_id

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

        combo_rule_id = kwargs.get("combo_rule_id")
        if pricelist and combo_rule_id:
            rule = self.env["product.pricelist.item"].sudo().browse(combo_rule_id)
            discount_percentage = 0.0
            if rule.compute_price == "percentage":
                discount_percentage = rule.percent_price
            elif rule.compute_price == "formula":
                discount_percentage = rule.price_discount

            data["extra_price"] -= data["extra_price"] * (discount_percentage / 100.0)

        website = self.env.website
        if website and website.show_line_subtotals_tax_selection == "tax_included":
            item_taxes = combo_item.product_id.taxes_id._filter_taxes_by_company(self.env.company)
            taxes = request.fiscal_position.map_tax(item_taxes)
            if taxes:
                tax_res = taxes.compute_all(
                    data["extra_price"],
                    currency,
                    1,
                    combo_item.product_id,
                    self.env.user.partner_id,
                )
                data["extra_price"] = tax_res["total_included"]

        return data
