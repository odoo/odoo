# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('procurement_group_id.stock_move_ids.created_purchase_line_ids.order_id', 'procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id', 'procurement_group_id.group_orig_ids.purchase_order_id')
    def _compute_purchase_order_count(self):
        super(SaleOrder, self)._compute_purchase_order_count()

    def _get_purchase_orders(self):
        mtso_purchase_orders = self._get_mtso_purchase_orders()
        return super()._get_purchase_orders() | self.procurement_group_id.stock_move_ids.created_purchase_line_ids.order_id | self.procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id | mtso_purchase_orders

    def _get_mtso_purchase_orders(self):
        return self.procurement_group_id.group_orig_ids.purchase_order_id

    def _action_cancel(self):
        """When Sale Orders have MTSO moves that have triggered the creation/update of Purchase Order lines,
        on the cancellation of those Sale Orders, decrease the qty of and/or cancel the Purchase Order lines.
        In the case all of the PO lines of a PO are cancelled, also cancel the PO."""
        so_mtso_moves = self.order_line.move_ids.filtered(lambda m: m._is_mtso())
        linked_po = self._get_mtso_purchase_orders().filtered(lambda po: po.state not in ('done', 'cancel'))
        if not so_mtso_moves or not linked_po.order_line:
            return super()._action_cancel()
        product_po_lines = linked_po.order_line.sorted(key='price_unit', reverse=True).grouped('product_id')  # TODO : the user may wants to use another key than price_unit (like delivery time, fiability...)
        products_to_decrease = {}
        for move in so_mtso_moves:
            # TODO: Ensure move uom and po lines uom are the same -> Force po uom
            if move.product_id not in product_po_lines:
                continue
            if move.product_id.id not in products_to_decrease:
                products_to_decrease[move.product_id.id] = [
                    0,
                    product_po_lines[move.product_id],
                ]
            # if move.product_uom != move.product_id.uom_id:
            products_to_decrease[move.product_id.id][0] += move.product_uom._compute_quantity(move.product_qty - move.quantity, move.product_id.uom_id)

        pol_to_remove = self.env['purchase.order.line']
        for _, values in products_to_decrease.items():
            tot_qty = values[0]
            for pol in values[1]:
                pol_product_uom_qty = pol.product_uom._compute_quantity(pol.product_qty, pol.product_id.uom_id)
                if float_compare(tot_qty, pol_product_uom_qty, precision_rounding=move.product_id.uom_id.rounding) < 0:
                    pol.product_qty = pol.product_id.uom_id._compute_quantity(pol_product_uom_qty - tot_qty, pol.product_uom)
                    break
                tot_qty -= pol_product_uom_qty
                pol_to_remove |= pol
        pol_to_remove.unlink()  # .product_qty = 0  # FIXME: Check with THD

        po_to_cancel = linked_po.filtered(lambda po: not po.order_line)
        po_to_cancel.button_cancel()
        return super()._action_cancel()
