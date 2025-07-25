# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PurchaseStockSuggestController(http.Controller):

    @http.route("/purchase_stock/update_purchase_suggest", type="jsonrpc", auth="user")
    def update_purchase_suggest(self, po_id, domain, suggest_ctx):
        """ Fetches all the product for a given domain (products in catalog), computes
        their suggested quantities, and returns estimated price of all suggestions """
        product_ids = request.env['product.product'].with_context(order_id=po_id).search(domain)
        suggest_ctx["suggest_product_ids"] = product_ids.ids
        po = request.env["purchase.order"].with_context(suggest_ctx).browse(po_id).ensure_one()
        return po.suggest_estimated_price
