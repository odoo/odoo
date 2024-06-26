# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _


class PurchaseOrder(models.Model):
    _inherit = 'repair.order'

    purchases_count = fields.Integer(compute="_compute_purchases_count", groups="purchase.group_purchase_user")

    def _compute_purchases_count(self):
        self.purchases_count = len(self._get_mto_links())

    def _get_mto_links(self):
        product_ids = [p.id for p in self.move_ids.product_id]
        domain = [
            ('state', 'in', ['draft', 'sent', 'to approve']),
            ('product_id', 'in', product_ids),
        ]
        if self.location_id.warehouse_id:
            domain += [(
                'order_id.picking_type_id.warehouse_id',
                '=', self.location_id.warehouse_id.id
            )]
        po_lines = self.env['purchase.order.line'].search(domain)
        return po_lines.mapped("order_id")

    def action_mto_links(self):
        self.ensure_one()
        po_lines = self._get_mto_links()

        if len(po_lines) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "views": [[False, "form"]],
                "res_id": po_lines.id,
            }
        return {
            "name": _("Purchase Orders"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [('id', 'in', po_lines.ids)],
        }
