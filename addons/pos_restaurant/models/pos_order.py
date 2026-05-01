# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index='btree_not_null', readonly=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.', readonly=True)
    course_ids = fields.One2many('restaurant.order.course', 'order_id', string="Courses")
    duration = fields.Char(string='Duration', compute='_compute_duration', help="Shows how long the table has been occupied.")

    def _compute_duration(self):
        current_time = fields.Datetime.now()
        for order in self:
            if not order._get_linked_table():
                order.duration = ""
                continue
            start_time = order.create_date
            end_time = current_time if order.state == "draft" else order.date_order
            duration_minutes = int((end_time - start_time).total_seconds() // 60)
            if duration_minutes <= 0:
                order.duration = ""
                continue
            hours, minutes = divmod(duration_minutes, 60)
            if hours:
                order.duration = f"{hours}h{minutes}'" if minutes else f"{hours}h"
            else:
                order.duration = f"{minutes}'"

    def _get_linked_table(self):
        return self.table_id

    def _get_open_order(self, order):
        config_id = self.env['pos.session'].browse(order.get('session_id')).config_id
        if not config_id.module_pos_restaurant:
            return super()._get_open_order(order)

        domain = []
        if order.get('table_id', False) and order.get('state') == 'draft':
            domain += ['|', ('uuid', '=', order.get('uuid')), '&', '&', ('table_id', '=', order.get('table_id')), ('state', '=', 'draft'), ('config_id', '=', config_id.id)]
        else:
            domain += [('uuid', '=', order.get('uuid'))]
        return self.env["pos.order"].search(domain, limit=1, order='id desc')

    def read_pos_data(self, data, config):
        result = super().read_pos_data(data, config)
        result['restaurant.order.course'] = self.env['restaurant.order.course']._load_pos_data_read(self.course_ids, config)
        return result
