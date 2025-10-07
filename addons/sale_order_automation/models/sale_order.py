from odoo import api, fields, models, exceptions


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super(SaleOrder, self.with_context(default_immediate_transfer=True)).action_confirm()
        for order in self:
            warehouse = order.warehouse_id
            if warehouse.is_delivery_set_to_done and order.picking_ids: 
                for picking in self.picking_ids:
                    picking.immediate_transfer = True
                    for move in picking.move_ids:
                        move.quantity_done = move.product_uom_qty
                    picking._autoconfirm_picking()
                    picking.action_set_quantities_to_reservation()
                    picking.action_confirm()
                    for move_line in picking.move_ids_without_package:
                        move_line.quantity_done = move_line.product_uom_qty
                    picking._action_done()
                    for mv_line in picking.move_ids.mapped('move_line_ids'):
                        if not mv_line.qty_done and mv_line.reserved_qty or mv_line.reserved_uom_qty:
                            mv_line.qty_done = mv_line.reserved_qty or mv_line.reserved_uom_qty
            if warehouse.create_invoice and not order.invoice_ids:
                order._create_invoices()
            if warehouse.validate_invoice and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.action_post()

        return res  
