# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    reinvoiced_so_count = fields.Integer(compute='_compute_reinvoiced_so_count')

    def _compute_reinvoiced_so_count(self):
        for order in self:
            order.reinvoiced_so_count = len(order.invoice_ids.invoice_line_ids.reinvoiced_so_line_id.order_id)

    def action_open_sale_orders(self):
        self.ensure_one()
        sale_orders = self.invoice_ids.invoice_line_ids.reinvoiced_so_line_id.order_id
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'context': {
                'create': False,
            }
        }
        if len(sale_orders) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': sale_orders.id,
            })
        else:
            action.update({
                'name': _('Re-Invoiced Sales Orders %s', self.name),
                'domain': [('id', 'in', sale_orders.ids)],
                'view_mode': 'list,form',
            })
        return action
