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
                params = self.env["pos.session"]._load_data_params(table_orders[0].config_id)
                result['pos.order'].extend(table_orders.read(params["pos.order"]["fields"], load=False))
                result['pos.payment'].extend(table_orders.payment_ids.read(params["pos.payment"]["fields"], load=False))
                result['pos.order.line'].extend(table_orders.lines.read(params["pos.order.line"]["fields"], load=False))
                result['pos.pack.operation.lot'].extend(table_orders.lines.pack_lot_ids.read(params["pos.pack.operation.lot"]["fields"], load=False))
                result["product.attribute.custom.value"].extend(table_orders.lines.custom_attribute_value_ids.read(params["product.attribute.custom.value"]["fields"], load=False))

        return result

    def _process_saved_order(self, draft):
        order_id = super()._process_saved_order(draft)
        self.send_table_count_notification(self.table_id)
        return order_id

    def send_table_count_notification(self, table_ids):
        messages = []
        a_config = None
        for config in self.env['pos.config'].search([('floor_ids', 'in', table_ids.floor_id.ids)]):
            if config.current_session_id:
                a_config = config
                order_count = config.get_tables_order_count_and_printing_changes()
                messages.append(('TABLE_ORDER_COUNT', order_count))
        if messages:
            a_config._notify(*messages, private=False)
