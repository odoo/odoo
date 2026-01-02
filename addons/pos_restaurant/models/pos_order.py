# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index='btree_not_null', readonly=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.', readonly=True)
    course_ids = fields.One2many('restaurant.order.course', 'order_id', string="Courses")

    def _get_open_order(self, order):
        config_id = self.env['pos.session'].browse(order.get('session_id')).config_id
        if not config_id.module_pos_restaurant:
            return super()._get_open_order(order)

        domain = []
        merge_table_id = order.get("table_id")

        # For self-ordering in service-at-table + pay-after-meal, fall back to the
        # self_ordering_table_id so orders from different devices can be merged when
        # opening the table on the floor screen.
        if (
            not merge_table_id
            and order.get("self_ordering_table_id")
            and config_id.self_ordering_service_mode == "table"
            and config_id.self_ordering_pay_after == "meal"
        ):
            merge_table_id = order.get("self_ordering_table_id")

        if merge_table_id and order.get("state") == "draft":
            domain += [
                "|",
                ("uuid", "=", order.get("uuid")),
                "|",
                "&",
                ("table_id", "=", merge_table_id),
                ("state", "=", "draft"),
                "&",
                ("self_ordering_table_id", "=", merge_table_id),
                ("state", "=", "draft"),
            ]
        else:
            domain += [("uuid", "=", order.get("uuid"))]
        return self.env["pos.order"].search(domain, limit=1, order='id desc')

    def read_pos_data(self, data, config):
        result = super().read_pos_data(data, config)
        result['restaurant.order.course'] = self.env['restaurant.order.course']._load_pos_data_read(self.course_ids, config)
        return result
