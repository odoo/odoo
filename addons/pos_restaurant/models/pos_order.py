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
        if order.get('table_id', False) and order.get('state') == 'draft':
            domain += ['|', ('uuid', '=', order.get('uuid')), ('table_id', '=', order.get('table_id')), ('state', '=', 'draft')]
        else:
            domain += [('uuid', '=', order.get('uuid'))]
        return self.env["pos.order"].search(domain, limit=1)

    @api.model
    def sync_from_ui(self, orders):
        result = super().sync_from_ui(orders)

        order_ids = self.browse([o['id'] for o in result["pos.order"]])
        if order_ids:
            config_id = order_ids.config_id.ids[0] if order_ids else False
            result['restaurant.order.course'] = order_ids.course_ids.read(order_ids.course_ids._load_pos_data_fields(config_id)) if config_id else []
        else:
            result['restaurant.order.course'] = []
        return result

    def _process_order(self, order, existing_order):
        restaurant_course_lines = order.pop("restaurant_course_lines", None)
        order_id = super()._process_order(order, existing_order)
        self._update_course_lines(order_id, restaurant_course_lines)
        return order_id

    def _update_course_lines(self, order_id, restaurant_course_lines):
        """
        Assigns the `course_id` field of order lines based on the relationship defined in the `order_course_lines` dictionary.
        This dictionary links each course UUID to its corresponding list of line UUIDs.
        """
        if not restaurant_course_lines:
            return
        courses = self.env['restaurant.order.course'].search_read([('order_id', '=', order_id)], fields=['uuid', 'id'], load=False)
        course_id_by_uuid = {c['uuid']: c['id'] for c in courses}
        line_uuids = set()
        for course_line_uuids in restaurant_course_lines.values():
            line_uuids.update(course_line_uuids)
        line_uuids = list(line_uuids)
        lines = self.env['pos.order.line'].search([('order_id', '=', order_id), ('uuid', 'in', line_uuids)])
        for course_uuid, line_uuids in restaurant_course_lines.items():
            course_id = course_id_by_uuid.get(course_uuid)
            if course_id:
                lines.filtered(lambda l: l.uuid in line_uuids).write({'course_id': course_id})
