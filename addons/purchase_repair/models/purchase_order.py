# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    repairs_count = fields.Integer(compute="_compute_repairs_count", groups="stock.group_stock_user")

    def _compute_repairs_count(self):
        self.repairs_count = len(self._get_repair_orders())

    def _get_repair_orders(self):
        product_ids = [p.id for p in self.order_line.product_id]
        domain = [
            ('state', 'not in', ['cancelled']),
            ('product_id', 'in', product_ids),
        ]
        if self.picking_type_id and self.picking_type_id.warehouse_id:
            domain += [
                ('repair_id.location_id.warehouse_id', '=',
                 self.picking_type_id.warehouse_id.id)
            ]
        ro_moves = self.env['stock.move'].search(domain)
        return ro_moves.mapped("repair_id")

    def action_show_mto_links(self):
        self.ensure_one()
        repair_orders = self._get_repair_orders()

        if len(repair_orders) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "repair.order",
                "views": [[False, "form"]],
                "res_id": repair_orders.id,
            }
        return {
            "name": _("Repair Orders"),
            "type": "ir.actions.act_window",
            "res_model": "repair.order",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [('id', 'in', repair_orders.ids)],
        }
