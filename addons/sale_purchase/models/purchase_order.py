# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sale_order_count = fields.Integer(
        "Number of Source Sale",
        compute='_compute_sale_order_count',
        groups='sales_team.group_sale_salesman')

    @api.depends('order_line.sale_order_id')
    def _compute_sale_order_count(self):
        for purchase in self:
            purchase.sale_order_count = len(purchase._get_sale_orders())

    def action_view_sale_orders(self):
        self.ensure_one()
        sale_order_ids = self._get_sale_orders().ids
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        }
        if len(sale_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': sale_order_ids[0],
            })
        else:
            action.update({
                'name': _('Sources Sale Orders %s', self.name),
                'domain': [('id', 'in', sale_order_ids)],
                'view_mode': 'list,form',
            })
        return action

    def button_cancel(self):
        result = super(PurchaseOrder, self).button_cancel()
        self.sudo()._activity_cancel_on_sale()
        return result

    def _get_sale_orders(self):
        return self.order_line.sale_order_id

    def _activity_cancel_on_sale(self):
        """ If some PO are cancelled, we need to put an activity on their origin SO (only the open ones). Since a PO can have
            been modified by several SO, when cancelling one PO, many next activities can be schedulded on different SO.
        """
        sale_to_notify_map = {}  # map SO -> recordset of PO as {sale.order: set(purchase.order.line)}
        for order in self:
            for purchase_line in order.order_line:
                if purchase_line.sale_line_id:
                    sale_order = purchase_line.sale_line_id.order_id
                    sale_to_notify_map.setdefault(sale_order, self.env['purchase.order.line'])
                    sale_to_notify_map[sale_order] |= purchase_line

        for sale_order, purchase_order_lines in sale_to_notify_map.items():
            sale_order._activity_schedule_with_view('mail.mail_activity_data_warning',
                user_id=sale_order.user_id.id or self.env.uid,
                views_or_xmlid='sale_purchase.exception_sale_on_purchase_cancellation',
                render_context={
                    'purchase_orders': purchase_order_lines.order_id,
                    'purchase_order_lines': purchase_order_lines,
            })


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_order_id = fields.Many2one(related='sale_line_id.order_id', string="Sale Order")
    sale_line_id = fields.Many2one('sale.order.line', string="Origin Sale Item", index='btree_not_null', copy=False)
