# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index='btree_not_null', readonly=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.', readonly=True)
    takeaway = fields.Boolean(string="Take Away", default=False)

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

    def _process_saved_order(self, draft):
        order_id = super()._process_saved_order(draft)
        if not self.env.context.get('cancel_table_notification'):
            self.send_table_count_notification(self.table_id)
        return order_id

    def send_table_count_notification(self, table_ids):
        messages = []
        a_config = []
        for config in self.env['pos.config'].search([('floor_ids', 'in', table_ids.floor_id.ids)]):
            if config.current_session_id:
                a_config.append(config)
                draft_order_ids = self.search([
                    ('table_id', 'in', table_ids.ids),
                    ('state', '=', 'draft')
                ]).ids
                messages.append(
                    (
                        "SYNC_ORDERS",
                        {
                            'login_number': self.env.context.get('login_number', False),
                            'order_ids': draft_order_ids,
                        }
                    )
                )
        if messages:
            for config in a_config:
                config._notify(*messages, private=False)

    def action_pos_order_cancel(self):
        super().action_pos_order_cancel()
        if self.table_id:
            self.send_table_count_notification(self.table_id)
