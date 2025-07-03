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
            domain += ['|', ('uuid', '=', order.get('uuid')), '&', ('table_id', '=', order.get('table_id')), ('state', '=', 'draft')]
        else:
            domain += [('uuid', '=', order.get('uuid'))]
        return self.env["pos.order"].search(domain, limit=1)

    def read_pos_data(self, data, config_id):
        result = super().read_pos_data(data, config_id)
        result['restaurant.order.course'] = self.course_ids.read(self.course_ids._load_pos_data_fields(config_id), load=False) if config_id else []
        return result
<<<<<<< b85e3fe518f6157cd403fe72dadbb998f817dc36
||||||| 2351aa29d33903aa6c57b68d9ff501653e9d50cb
    
=======

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
>>>>>>> 8776b61a98e0dec071187cb8a32b43cc201a3f3d
