# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools import SQL

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
        if order.get('table_id', False) and order.get('state') == 'draft':
            # Concurrent syncs on the same table conflict here and get retried, finding this open order.
            # A real UPDATE is needed instead of a lock (FOR UPDATE): a lock alone doesn't raise a
            # serialization failure if the other transaction already committed after our snapshot,
            # so the open order wouldn't be visible and a duplicate would be created.
            self.env.cr.execute(SQL("UPDATE restaurant_table SET write_date = write_date WHERE id = %s", order['table_id']))
            domain += ['|', ('uuid', '=', order.get('uuid')), '&', '&', ('table_id', '=', order.get('table_id')), ('state', '=', 'draft'), ('config_id', '=', config_id.id)]
        else:
            domain += [('uuid', '=', order.get('uuid'))]
        return self.env["pos.order"].search(domain, limit=1, order='id desc')

    def read_pos_data(self, data, config):
        result = super().read_pos_data(data, config)
        result['restaurant.order.course'] = self.env['restaurant.order.course']._load_pos_data_read(self.course_ids, config)
        return result
