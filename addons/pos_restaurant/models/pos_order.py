# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import partial

from odoo import api, fields, models
from re import search


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    note = fields.Char('Note added by the waiter.')
    mp_skip = fields.Boolean('Skip line when sending ticket to kitchen printers.')
    mp_dirty = fields.Boolean()
    mp_hash = fields.Char(string='Multiprint ID', help='Used for the multiprint feature. To aid the proper computation of changes in the order.')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.')
    multiprint_resume = fields.Char()

    @api.model
    def get_table_draft_orders(self, table_id):
        """Returns order data of the given table.
        We also compute the uid for each order and assigned it as order_id and pos_order_id
        for the orderlines and payments, respectively. This is to make sure that the returned
        orders are compatible with the orders in the frontend.
        """
        orders = self.search([('state', '=', 'draft'), ('table_id', '=', table_id)])
        data = orders.export_for_ui()['data']
        order_uid_map = {}
        for order in data['pos.order']:
            order_uid = search(r"\d{5,}-\d{3,}-\d{4,}", order['pos_reference']).group(0)
            order_uid_map[order['id']] = order_uid
            order['server_id'] = order['id']
            order['id'] = order_uid

        for orderline in data['pos.order.line']:
            original_order_id = orderline['order_id']
            orderline['order_id'] = order_uid_map[original_order_id]

        for payment in data['pos.payment']:
            original_order_id = payment['pos_order_id']
            payment['pos_order_id'] = order_uid_map[original_order_id]

        return data

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
        order_fields['multiprint_resume'] = ui_order.get('multiprint_resume', False)
        return order_fields
