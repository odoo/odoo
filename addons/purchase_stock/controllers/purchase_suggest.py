# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PurchaseStockSuggestController(http.Controller):

    @http.route('/purchase_stock/init_purchase_suggest', type='jsonrpc', auth='user')
    def init_purchase_suggest_wizard(self, po_id, domain):
        """ Instantiates and fetches default values for the suggest wizard """
        order = request.env['purchase.order'].browse([po_id])
        defaults = {}
        for field in ("based_on", "number_of_days", "percent_factor"):
            default = request.env["ir.default"]._get(
                "purchase.order.suggest",
                field,
                company_id=request.env.company.id,
                condition=f"partner_id={order.partner_id.id}")
            if default is not None:
                defaults[field] = default

        wiz = request.env['purchase.order.suggest'].create({'purchase_order_id': order.id, **defaults})

        return {
            'wizardId': wiz.id,
            'basedOnOptions': wiz.fields_get(['based_on'])['based_on']['selection'],
            'basedOn': wiz.based_on,
            'numberOfDays': wiz.number_of_days,
            'multiplier': wiz.multiplier,
            'vendorName': order.partner_id.display_name,
            'currencySymbol': wiz.currency_id.symbol,
            'percentFactor': wiz.percent_factor,
        }

    @http.route("/purchase_stock/update_purchase_suggest", type="jsonrpc", auth="user")
    def update_purchase_suggest(self, po_id, wizard_id, domain, suggest_ctx):
        """ Update suggest wizard and returns computed fields on purchase_order"""
        wiz = request.env["purchase.order.suggest"].browse(wizard_id).ensure_one()
        wiz.write({
            "based_on": suggest_ctx["suggest_based_on"],
            "number_of_days": suggest_ctx["suggest_number_days"],
            "percent_factor": suggest_ctx["suggest_percent"],
        })
        product_ids = request.env['product.product'].with_context(order_id=po_id).search(domain)
        suggest_ctx = {
            **suggest_ctx,
            "suggest_multiplier": wiz.multiplier,
            "suggest_product_ids": product_ids.ids,
        }
        po = request.env["purchase.order"].with_context(suggest_ctx).browse(po_id).ensure_one()

        return {
            "estimatedPrice": po.suggest_estimated_price,
            'multiplier': wiz.multiplier,
        }
