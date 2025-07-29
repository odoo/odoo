# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index='btree_not_null', readonly=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.', readonly=True)
    takeaway = fields.Boolean(string="Take Away", default=False)

    def _get_open_order(self, order):
        config_id = self.env['pos.session'].browse(order.get('session_id')).config_id
        if not config_id.module_pos_restaurant:
            return super()._get_open_order(order)

        domain = []
        if order.get('table_id', False) and order.get('state') == 'draft':
            domain += ['|', ('uuid', '=', order.get('uuid')), '&', ('table_id', '=', order.get('table_id')), ('state', '=', 'draft')]
        else:
            domain += [('uuid', '=', order.get('uuid'))]
        return self.env["pos.order"].search(domain, limit=1)

    @api.model
    def remove_from_ui(self, server_ids):
        tables = self.env['pos.order'].search([('id', 'in', server_ids)]).table_id
        order_ids = super().remove_from_ui(server_ids)
        self.send_table_count_notification(tables)
        return order_ids

    @api.model
    def sync_from_ui(self, orders):
        result = super().sync_from_ui(orders)

        if self.env.context.get('table_ids'):
            order_ids = [order['id'] for order in result['pos.order']]
            table_orders = self.search([
                "&",
                ('table_id', 'in', self.env.context['table_ids']),
                ('state', '=', 'draft'),
                ('id', 'not in', order_ids)
            ])

            if len(table_orders) > 0:
                config_id = table_orders[0].config_id.id
                result['pos.order'].extend(table_orders.read(table_orders._load_pos_data_fields(config_id), load=False))
                result['pos.payment'].extend(table_orders.payment_ids.read(table_orders.payment_ids._load_pos_data_fields(config_id), load=False))
                result['pos.order.line'].extend(table_orders.lines.read(table_orders.lines._load_pos_data_fields(config_id), load=False))
                result['pos.pack.operation.lot'].extend(table_orders.lines.pack_lot_ids.read(table_orders.lines.pack_lot_ids._load_pos_data_fields(config_id), load=False))
                result["product.attribute.custom.value"].extend(table_orders.lines.custom_attribute_value_ids.read(table_orders.lines.custom_attribute_value_ids._load_pos_data_fields(config_id), load=False))

        return result

    def send_table_count_notification(self, table_ids):
         # Cannot remove the method in stable
        pass

    def action_pos_order_cancel(self):
        result = super().action_pos_order_cancel()
        if self.table_id:
            self.send_table_count_notification(self.table_id)
        return result

    def set_tip(self, tip_amount, payment_line_id):
        """Update tip state on `self` and the tip amount on the payment line."""

        self.ensure_one()

        payment_line = self.payment_ids.filtered(lambda line: line.id == payment_line_id)
        payment_line.write({
            'amount': payment_line.amount + tip_amount,
        })
        self.write({
            "is_tipped": True,
            "tip_amount": tip_amount,
        })
