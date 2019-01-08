# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class LunchCashMove(models.Model):
    """ Two types of cashmoves: payment (credit) or order (debit) """
    _name = 'lunch.cashmove'
    _description = 'Lunch Cashmove'

    user_id = fields.Many2one('res.users', 'User',
                              default=lambda self: self.env.uid)
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    amount = fields.Float('Amount', required=True, help='Can be positive (payment) or negative (order or payment if user wants to get his money back)')
    description = fields.Text('Description', help='Can be an order or a payment')
    order_id = fields.Many2one('lunch.order.line', 'Order', ondelete='cascade')
    state = fields.Selection([('order', 'Order'), ('payment', 'Payment')],
                             'Is an order or a payment', default='payment')

    @api.multi
    def name_get(self):
        return [(cashmove.id, '%s %s' % (_('Lunch Cashmove'), '#%d' % cashmove.id)) for cashmove in self]
