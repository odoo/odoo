from odoo.http import route
from odoo.libs.debug_log import DebugLog

from odoo.addons.product.controllers.catalog import ProductCatalogController

_debug = DebugLog(__name__)


class ProductCatalogAccountController(ProductCatalogController):
    @route("/product/catalog/get_sections", auth="user", type="jsonrpc", readonly=True)
    def product_catalog_get_sections(self, res_model, order_id, child_field, **kwargs):
        _debug.pipeline(
            "route",
            handler="ProductCatalogAccountController.product_catalog_get_sections",
        )
        order = self._get_order(res_model, order_id)
        return order.with_company(order.company_id)._get_sections(child_field, **kwargs)

    @route("/product/catalog/create_section", auth="user", type="jsonrpc")
    def product_catalog_create_section(
        self,
        res_model,
        order_id,
        child_field,
        name,
        position,
        **kwargs,
    ):
        _debug.pipeline(
            "route",
            handler="ProductCatalogAccountController.product_catalog_create_section",
        )
        order = self._get_order(res_model, order_id)
        return order.with_company(order.company_id)._create_section(
            child_field,
            name,
            position,
            **kwargs,
        )

    @route("/product/catalog/resequence_sections", auth="user", type="jsonrpc")
    def product_catalog_resequence_sections(
        self,
        res_model,
        order_id,
        sections,
        child_field,
        **kwargs,
    ):
        _debug.pipeline(
            "route",
            handler="ProductCatalogAccountController.product_catalog_resequence_sections",
        )
        order = self._get_order(res_model, order_id)
        return order.with_company(order.company_id)._resequence_sections(
            sections,
            child_field,
            **kwargs,
        )
