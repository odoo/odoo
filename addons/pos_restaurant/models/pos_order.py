# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import partial

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    note = fields.Char('Internal Note added by the waiter.')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index='btree_not_null', readonly=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.', readonly=True)

    @api.model
    def remove_from_ui(self, server_ids):
        tables = self.env['pos.order'].search([('id', 'in', server_ids)]).table_id
        order_ids = super().remove_from_ui(server_ids)
        self.send_table_count_notification(tables)
        return order_ids

    def _process_saved_order(self, draft):
        order_id = super()._process_saved_order(draft)
        self.send_table_count_notification(self.table_id)
        return order_id

    def send_table_count_notification(self, table_ids):
        messages = []
        for config in self.env['pos.config'].search([('floor_ids', 'in', table_ids.floor_id.ids)]):
            config_cur_session = config.current_session_id
            if config_cur_session:
                order_count = config.get_tables_order_count_and_printing_changes()
                messages.append((config_cur_session._get_bus_channel_name(), 'TABLE_ORDER_COUNT', order_count))
        self.env['bus.bus']._sendmany(messages)

    def set_tip(self, tip_line_vals):
        """Set tip to `self` based on values in `tip_line_vals`."""

        self.ensure_one()
        PosOrderLine = self.env['pos.order.line']
        process_line = partial(PosOrderLine._order_line_fields, session_id=self.session_id.id)

        # 1. add/modify tip orderline
        processed_tip_line_vals = process_line([0, 0, tip_line_vals])[2]
        processed_tip_line_vals.update({ "order_id": self.id })
        tip_line = self.lines.filtered(lambda line: line.product_id == self.session_id.config_id.tip_product_id)
        if not tip_line:
            tip_line = PosOrderLine.create(processed_tip_line_vals)
        else:
            tip_line.write(processed_tip_line_vals)

        # 2. modify payment
        payment_line = self.payment_ids.filtered(lambda line: not line.is_change)[0]
        # TODO it would be better to throw error if there are multiple payment lines
        # then ask the user to select which payment to update, no?
        payment_line._update_payment_line_for_tip(tip_line.price_subtotal_incl)

        # 3. flag order as tipped and update order fields
        self.write({
            "is_tipped": True,
            "tip_amount": tip_line.price_subtotal_incl,
            "amount_total": self.amount_total + tip_line.price_subtotal_incl,
            "amount_paid": self.amount_paid + tip_line.price_subtotal_incl,
        })

    def set_no_tip(self):
        """Override this method to introduce action when setting no tip."""
        self.ensure_one()
        self.write({
            "is_tipped": True,
            "tip_amount": 0,
        })

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['table_id'] = ui_order.get('table_id', False)
        order_fields['customer_count'] = ui_order.get('customer_count', 0)
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result['table_id'] = order.table_id.id
        result['customer_count'] = order.customer_count
        return result

    @api.model
    def export_for_ui_table_draft(self, table_ids):
        orders = self.env['pos.order'].search([('state', '=', 'draft'), ('table_id', 'in', table_ids)])
        return orders.export_for_ui()
