# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    reinvoiced_so_count = fields.Integer(compute='_compute_reinvoiced_so_count')

    def _compute_reinvoiced_so_count(self):
        for order in self:
            order.reinvoiced_so_count = len(order.invoice_ids.invoice_line_ids.reinvoiced_sale_line_id.order_id)

    def action_open_sale_orders(self):
        self.ensure_one()
        sale_orders = self.invoice_ids.invoice_line_ids.reinvoiced_sale_line_id.order_id
        action = {
            'name': _('Re-Invoiced Sales Orders %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,kanban,form,calendar,pivot,graph,activity',
            'context': {
                'create': False,
            },
        }
        if len(sale_orders) == 1:
            action.update({
                'res_id': sale_orders.id,
                'view_mode': 'form',
            })
        else:
            action['domain'] = [('id', 'in', sale_orders.ids)]
        return action
