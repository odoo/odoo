# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class LunchOrderLineWizard(models.TransientModel):
    _name = 'lunch.order.line.temp'
    _description = 'Lunch Order Line Temp'

    product_id = fields.Many2one('lunch.product', string='Product ID')
    product_description = fields.Text('Description', related='product_id.description')
    product_name = fields.Char('Product', related='product_id.name')
    product_supplier = fields.Many2one('lunch.supplier', related='product_id.supplier_id')
    topping_ids = fields.Many2many('lunch.product', string="Extra Garniture", domain="[('is_topping', '=', True), ('supplier_id', '=', product_supplier)]")

    quantity = fields.Float('Quantity', default=1)
    price_total = fields.Float('Total Price', compute='_compute_price_total')
    note = fields.Text('Special Instructions')

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)

    @api.depends('product_id', 'topping_ids', 'quantity')
    def _compute_price_total(self):
        for wizard in self:
            wizard.price_total = wizard.quantity * sum(record.price for record in (wizard.product_id | wizard.topping_ids))

    def find_current_order(self):
        order_id = self.env['lunch.order'].search([('state', '!=', 'cancel'),
                                                   ('user_id', '=', self.user_id.id),
                                                   ('date', '=', fields.Date.today())], limit=1)
        if not order_id:
            order_id = self.env['lunch.order'].create({})
        return order_id

    def add_to_cart(self):
        self.ensure_one()

        order_id = self.find_current_order()

        # Do not add a line to confirmed orders as they are uneditable
        if order_id.state == 'confirmed':
            return

        lines = order_id.order_line_ids.filtered(lambda line: line.product_id == self.product_id and line.topping_ids == self.topping_ids)

        if lines:
            line = lines[0]
            line.quantity += 1
        else:
            line = self.env['lunch.order.line'].create({
                'order_id': order_id.id,
                'product_id': self.product_id.id,
                'topping_ids': [(6, 0, self.topping_ids.ids)],
                'quantity': self.quantity,
            })
            wallet_balance = self.env['lunch.cashmove'].get_wallet_balance(self.user_id)
            if wallet_balance < line.price:
                raise UserError(_('Your wallet does not contain enough money to order that.'
                                  'To add some money to your wallet, please contact your lunch manager.'))

        if order_id.state == 'ordered':
            # Need to update cashmove
            cashmove = self.env['lunch.cashmove'].search([('order_line_id', '=', line.id)], limit=1)
            if cashmove:
                cashmove.amount = -line.price
            else:
                self.env['lunch.cashmove'].create({
                    'order_line_id': line.id,
                    'user_id': line.user_id.id,
                    'description': line.product_id.name,
                    'state': 'order',
                    'date': line.date,
                    'amount': -line.price,
                })
