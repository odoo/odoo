from odoo import _
from odoo.exceptions import UserError
from odoo.http import Controller, request, route


class ProductCatalogController(Controller):
    @staticmethod
    def _get_order(res_model, order_id, allow_unsaved=False):
        env = request.env
        if res_model not in env.registry or not isinstance(
            env[res_model], env.registry["mixin.product.catalog"]
        ):
            raise UserError(_("The product catalog cannot be used on this model."))
        if allow_unsaved and not order_id:
            return env[res_model]
        try:
            order_id = int(order_id)
        except ValueError, TypeError:
            raise UserError(_("The requested record does not exist.")) from None
        order = env[res_model].browse(order_id).exists()
        if not order:
            raise UserError(_("The requested record does not exist."))
        return order

    @route(
        "/product/catalog/order_lines_info", auth="user", type="jsonrpc", readonly=True
    )
    def product_catalog_get_order_lines_info(
        self, res_model, order_id, product_ids, **kwargs
    ):
        order = self._get_order(res_model, order_id, allow_unsaved=True)
        return order.with_company(
            order.company_id
        )._get_product_catalog_order_line_info(
            product_ids,
            **kwargs,
        )

    @route("/product/catalog/update_order_line_info", auth="user", type="jsonrpc")
    def product_catalog_update_order_line_info(
        self, res_model, order_id, product_id, quantity=0, **kwargs
    ):
        order = self._get_order(res_model, order_id)
        if order._is_readonly():
            raise UserError(_("You cannot edit the products of a read-only record."))
        return order.with_company(order.company_id)._update_order_line_info(
            product_id,
            quantity,
            **kwargs,
        )
