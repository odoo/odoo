# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from uuid import uuid4


class RestaurantOrderCourse(models.Model):
    _name = 'restaurant.order.course'
    _description = 'POS Restaurant Order Course'
    _inherit = ['pos.load.mixin']

    fired = fields.Boolean(string="Fired", default=False)
    fired_date = fields.Datetime(string="Fired Date")
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    index = fields.Integer(string="Course index", default=0)
    order_id = fields.Many2one('pos.order', string='Order Ref', required=True, index=True, ondelete='cascade')
    line_ids = fields.One2many('pos.order.line', 'course_id', string="Order Lines", readonly=True)

    def write(self, vals):
        if vals.get('fired') and not self.fired_date:
            vals['fired_date'] = fields.Datetime.now()
        return super().write(vals)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('order_id', 'in', [order['id'] for order in data['pos.order']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['uuid', 'fired', 'order_id', 'line_ids', 'index', 'write_date']
