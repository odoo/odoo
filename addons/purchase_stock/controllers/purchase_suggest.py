# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PurchaseStockSuggestController(http.Controller):

    @http.route('/purchase_stock/init_purchase_suggest', type='jsonrpc', auth='user')
    def init_purchase_suggest_wizard(self, po_id, domain):
        """ Instantiates and fetches default values for the suggest wizard """
        order = request.env['purchase.order'].browse([po_id])
        product_ids = request.env['product.product'].with_context(order_id=order.id).search(domain).ids

        if not product_ids:
            return {'showSuggest': 0}

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
            'multiplier': wiz.multiplier,
            'vendorName': order.partner_id.display_name,
            'currencySymbol': wiz.currency_id.symbol,
            'percentFactor': wiz.percent_factor,
            'showSuggest': 1,
            'warehouseId': wiz.warehouse_id.id,
        }

    @http.route("/purchase_stock/update_purchase_suggest", type="jsonrpc", auth="user")
    def update_purchase_suggest(self, wizard_id, vals):
        """ Update suggest wizard and returns computed fields (will do more in future)"""
        wiz = request.env["purchase.order.suggest"].browse(wizard_id).ensure_one()
        wiz.write(vals)

        return {
            "estimatedPrice": wiz.estimated_price,
            'multiplier': wiz.multiplier,
        }

    # TODO Finish migration
    # @http.route("/purchase_stock/action_purchase_suggest", type="jsonrpc", auth="user")
    # def action_purchase_order_suggest(self, po_id, product_context):
    #     """ Auto-fill the Purchase Order with vendor's product regarding the
    #     past demand (real consumtion for a given period of time.)"""

    #     order = request.env['purchase.order'].browse([po_id])
    #     # Products are either the given products, either the supplier's products.
    #     supplierinfos = self.env['product.supplierinfo'].search([
    #         ('partner_id', '=', order.partner_id.id),
    #     ])
    #     products = self.product_ids or supplierinfos.product_id
    #     products = products.with_context(product_context)

    #     # Create new PO lines for each product with a monthy demand.
    #     po_lines_commands = []
    #     for product in products:
    #         existing_po_lines = order.order_line.filtered(lambda pol: pol.product_id == product)
    #         existing_po_line = existing_po_lines[:1]
    #         # If there is multiple lines for the same product, we delete all the
    #         # lines except the first one (who will be updated.)
    #         for po_line in existing_po_lines[1:]:
    #             po_lines_commands.append(Command.unlink(po_line.id))

    #         if self.based_on == 'actual_demand':
    #             quantity = ceil(product.outgoing_qty * (self.percent_factor / 100))
    #         else:
    #             quantity = ceil(product.monthly_demand * self.multiplier)
    #         qty_to_deduce = max(product.qty_available, 0) + max(product.incoming_qty, 0)
    #         quantity -= qty_to_deduce
    #         if quantity <= 0:
    #             # If there is no quantity for a filtered product and there is an
    #             # existing PO line for this product, we delete it.
    #             if existing_po_line:
    #                 po_lines_commands.append(Command.unlink(existing_po_line.id))
    #             continue
    #         supplierinfo = supplierinfos.filtered(lambda supinfo: supinfo.product_id == product)[:1]
    #         if existing_po_line:
    #             # If a PO line already exists for this product, we simply update its quantity.
    #             vals = self.env['purchase.order.line']._prepare_purchase_order_line(
    #                 product,
    #                 quantity,
    #                 product.uom_id,
    #                 order.company_id,
    #                 supplierinfo,
    #                 order
    #             )
    #             po_lines_commands.append(Command.update(existing_po_line.id, vals))
    #         else:
    #             # If not, we create a new PO line.
    #             vals = self.env['purchase.order.line']._prepare_purchase_order_line(
    #                 product,
    #                 quantity,
    #                 product.uom_id,
    #                 order.company_id,
    #                 supplierinfo,
    #                 order
    #             )
    #             po_lines_commands.append(Command.create(vals))
    #     order.order_line = po_lines_commands
    #     self._save_values_for_vendor()
    #     return {
    #         'type': 'ir.actions.act_window_close',
    #         'infos': {'refresh': True},
    #     }
