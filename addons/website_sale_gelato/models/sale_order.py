from odoo import _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        product = self.env["product.product"].browse(product_id)
        mixing_products = product.type != "service" and any(
            (product.gelato_product_uid and not line.product_id.gelato_product_uid)
            or (not product.gelato_product_uid and line.product_id.gelato_product_uid)
            for line in self.line_ids.filtered(lambda l: l.product_id.type != "service")
        )
        if mixing_products:
            _debug.logic(
                "gelato_mixed_cart_refused",
                order=self,
                product=product,
                gelato=bool(product.gelato_product_uid),
            )
            return 0, _(
                "The product %(product_name)s cannot be added to the cart as it requires separate"
                " shipping. Please place your order for the current cart first.",
                product_name=product.name,
            )
        return super()._get_updated_quantity(
            order_line, product_id, new_qty, uom_id, **kwargs
        )
