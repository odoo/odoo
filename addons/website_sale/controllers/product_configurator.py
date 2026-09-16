from odoo.http import request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_is_zero

from odoo.addons.sale.controllers.product_configurator import (
    SaleProductConfiguratorController,
)
from odoo.addons.website_sale.controllers.main import WebsiteSale

_debug = DebugLog(__name__)


class WebsiteSaleProductConfiguratorController(
    SaleProductConfiguratorController, WebsiteSale
):
    @route(
        route="/website_sale/should_show_product_configurator",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def website_sale_should_show_product_configurator(
        self, product_template_id, ptav_ids, is_product_configured
    ):
        product_template = request.env["product.template"].browse(product_template_id)
        combination = request.env["product.template.attribute.value"].browse(ptav_ids)
        single_product_variant = product_template.get_single_product_variant()
        has_optional_products = bool(
            product_template.optional_product_ids.filtered(
                lambda op: self._is_product_shown(op, combination)
            )
        )
        _debug.logic(
            "product_configurator",
            template=product_template_id,
            optional=has_optional_products,
            configured=is_product_configured,
        )
        return has_optional_products or not (
            single_product_variant.get("product_id") or is_product_configured
        )

    def _get_product_template(self, product_template_id):
        if request.is_frontend:
            combo_item = (
                request.env["product.combo.item"]
                .sudo()
                .search(
                    [
                        ("product_id.product_tmpl_id.id", "=", product_template_id),
                    ]
                )
            )
            if combo_item and request.env["product.template"].sudo().search_count(
                [
                    ("combo_ids", "in", combo_item.mapped("combo_id.id")),
                    ("website_published", "=", True),
                ],
                limit=1,
            ):
                _debug.logic(
                    "configurator_template",
                    by="published_combo",
                    template=product_template_id,
                )
                return (
                    request.env["product.template"].sudo().browse(product_template_id)
                )
        return super()._get_product_template(product_template_id)

    @route(
        route="/website_sale/product_configurator/get_values",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def website_sale_product_configurator_get_values(self, *args, **kwargs):
        self._update_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_get_values(*args, **kwargs)

    @route(
        route="/website_sale/product_configurator/create_product",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def website_sale_product_configurator_create_product(self, *args, **kwargs):
        _debug.lifecycle("configurator_variant_created")
        return super().sale_product_configurator_create_product(*args, **kwargs)

    @route(
        route="/website_sale/product_configurator/update_combination",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def website_sale_product_configurator_update_combination(self, *args, **kwargs):
        self._update_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_update_combination(*args, **kwargs)

    @route(
        route="/website_sale/product_configurator/get_optional_products",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def website_sale_product_configurator_get_optional_products(self, *args, **kwargs):
        self._update_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_get_optional_products(*args, **kwargs)

    def _get_basic_product_information(
        self,
        product_or_template,
        pricelist,
        combination,
        currency=None,
        date=None,
        **kwargs,
    ):
        basic_product_information = super()._get_basic_product_information(
            product_or_template.with_context(
                display_default_code=not request.is_frontend
            ),
            pricelist,
            combination,
            currency=currency,
            date=date,
            **kwargs,
        )

        if request.is_frontend:
            has_zero_price = float_is_zero(
                basic_product_information["price"], precision_rounding=currency.rounding
            )
            basic_product_information["can_be_sold"] = not (
                request.website.prevent_zero_price_sale and has_zero_price
            )
            strikethrough_price = (
                self._get_strikethrough_price(
                    product_or_template.with_context(
                        **product_or_template._prepare_product_price_context(
                            combination
                        )
                    ),
                    currency,
                    date,
                    basic_product_information["price"],
                    basic_product_information["pricelist_rule_id"],
                )
                if "price_info" not in basic_product_information
                else None
            )
            if strikethrough_price:
                basic_product_information["strikethrough_price"] = strikethrough_price
        return basic_product_information

    def _get_ptav_price_extra(self, ptav, currency, date, product_or_template):
        price_extra = super()._get_ptav_price_extra(
            ptav, currency, date, product_or_template
        )
        if request.is_frontend:
            return self._apply_taxes_to_price(
                price_extra, product_or_template, currency
            )
        return price_extra

    def _get_strikethrough_price(
        self, product_or_template, currency, date, price, pricelist_rule_id=None
    ):
        pricelist_rule = request.env["product.pricelist.item"].browse(pricelist_rule_id)

        if pricelist_rule._show_discount_on_shop():
            pricelist_base_price = self._apply_taxes_to_price(
                pricelist_rule._get_price_before_discount(
                    product=product_or_template,
                    quantity=1.0,
                    uom=product_or_template.uom_id,
                    date=date,
                    currency=currency,
                ),
                product_or_template,
                currency,
            )
            if currency.compare_amounts(pricelist_base_price, price) == 1:
                return pricelist_base_price

        if (
            request.env["res.groups"]._is_feature_enabled(
                "website_sale.group_product_price_comparison"
            )
            and product_or_template.compare_list_price
        ):
            compare_list_price = product_or_template.currency_id._convert(
                from_amount=product_or_template.compare_list_price,
                to_currency=currency,
                company=request.env.company,
                date=date,
                round=False,
            )
            if currency.compare_amounts(compare_list_price, price) == 1:
                return compare_list_price
        return None

    def _is_product_shown(self, product_template, parent_combination):
        should_show_product = super()._is_product_shown(
            product_template, parent_combination
        )
        if request.is_frontend:
            return (
                should_show_product
                and product_template._is_add_to_cart_possible(parent_combination)
                and product_template.filtered_domain(request.website.website_domain())
            )
        return should_show_product

    @staticmethod
    def _apply_taxes_to_price(price, product_or_template, currency):
        product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(
            request.env.company
        )
        if product_taxes:
            taxes = request.fiscal_position.map_tax(product_taxes)
            return request.env["product.template"]._apply_taxes_to_price(
                price,
                currency,
                product_taxes,
                taxes,
                product_or_template,
                website=request.website,
            )
        return price
