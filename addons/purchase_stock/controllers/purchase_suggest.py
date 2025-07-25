# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PurchaseStockSuggestController(http.Controller):

    @http.route('/purchase_stock/init_purchase_suggest', type='jsonrpc', auth='user')
    def init_purchase_suggest_wizard(self, po_id, domain):
        """ Instantiates and fetches default values for the suggest wizard """
        order = request.env['purchase.order'].browse([po_id])
        product_ids = request.env['product.product'].with_context(order_id=order.id).search(domain).ids

        defaults = {}
        for field in ("based_on", "number_of_days", "percent_factor"):
            default = request.env["ir.default"]._get(
                "purchase.order.suggest",
                field,
                company_id=request.env.company.id,
                condition=f"partner_id={order.partner_id.id}")
            if default is not None:
                defaults[field] = default

        wiz = (
            request.env['purchase.order.suggest']
            .with_context({
                'default_purchase_order_id': order.id,
                'default_warehouse_id': order.picking_type_id.warehouse_id.id,
                'default_product_ids': product_ids,
            })
            .create({'purchase_order_id': order.id, **defaults})
        )

        return {
            'wizardId': wiz.id,
            'basedOnOptions': wiz.fields_get(['based_on'])['based_on']['selection'],
            'basedOn': wiz.based_on,
            'numberOfDays': wiz.number_of_days,
            'vendorName': order.partner_id.display_name,
            'currencySymbol': wiz.currency_id.symbol,
            'percentFactor': wiz.percent_factor,
        }

    @http.route("/purchase_stock/update_purchase_suggest", type="jsonrpc", auth="user")
    def update_purchase_suggest(self, wizard_id, vals):
        """ Update suggest wizard and returns computed fields (will do more in future)"""
        wiz = request.env["purchase.order.suggest"].browse(wizard_id).ensure_one()
        wiz.write(vals)

        return {"estimatedPrice": wiz.estimated_price}
