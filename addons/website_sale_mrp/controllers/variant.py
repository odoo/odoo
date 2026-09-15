from odoo.http import request, route
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_sale_stock.controllers.variant import (
    WebsiteSaleStockVariantController,
)

_debug = DebugLog(__name__)


class WebsiteSaleMrpVariantController(WebsiteSaleStockVariantController):
    @route(
        "/website_sale_mrp/get_unavailable_qty_from_kits",
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def get_unavailable_qty_from_kits(self, product_id=None, *args, **kwargs):
        so = request.cart
        if not so:
            _debug.logic("kit_availability_without_cart", product=product_id)
            return 0
        product = request.env["product.product"].browse(product_id)
        with _debug.perf(
            "unavailable_qty_from_kits", cr=request.env.cr, order=so, product=product
        ):
            return so._get_unavailable_quantity_from_kits(product)
