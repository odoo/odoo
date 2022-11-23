# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError


import random


readonly_fields_states = {
        state: [('readonly', True)]
        for state in {'sale', 'done', 'cancel'}
}


class SaleOrders(models.Model):
    _inherit = ["sale.order"]

    test = fields.Char(string="Test",
                       default=lambda x: random.randint(1, 10),
                       states=readonly_fields_states)

    @api.constrains('test')
    def check_test_length(self):
        for rec in self:
            if rec.test:
                if len(rec.test) > 50:
                    raise ValidationError('Длина текста строки "test" должна быть меньше 50 символов!')
            else:
                pass

    @api.onchange('order_line', 'date_order')
    @api.depends('order_line.price_total', 'date_order')
    def _onchange_amount_total_date_order(self):
        ran_num = random.randint(1, 10)
        for order in self:
            if order.amount_total:
                amount = f'{order.amount_total}-{order.date_order}'
                order.write({'test': amount})
            else:
                order.write({'test': ran_num})

