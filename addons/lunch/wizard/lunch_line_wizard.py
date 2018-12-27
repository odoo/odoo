# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class LunchOrderLineWizard(models.TransientModel):
    _name = 'lunch.order.line.temp'
    _description = 'Lunch Order Line Temp'

    def _default_topping_ids(self):
        last_time_ordered = self.env['lunch.order.line'].search([('product_id', '=', self.env.context.get('default_product_id', 0))],
                                                                order="date desc", limit=1)
        return last_time_ordered.topping_ids

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)

    product_id = fields.Many2one('lunch.product', string='Product ID')
    product_description = fields.Text('Description', related='product_id.description')
    product_name = fields.Char('Product', related='product_id.name')
    product_category = fields.Many2one('lunch.product.category', related='product_id.category_id')
    topping_ids = fields.Many2many('lunch.topping', string="Extra Garniture", domain="[('category_id', '=', product_category)]", default=_default_topping_ids)

    available_toppings = fields.Boolean(help='Are toppings available for this product', compute='_compute_available_toppings')

    quantity = fields.Float('Quantity', default=1)
    price_total = fields.Float('Total Price', compute='_compute_price_total')
    note = fields.Text('Special Instructions')

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)

    @api.depends('product_id')
    def _compute_available_toppings(self):
        for wizard in self:
            wizard.available_toppings = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id)]))

    @api.depends('product_id', 'topping_ids', 'quantity')
    def _compute_price_total(self):
        for wizard in self:
            wizard.price_total = wizard.quantity * (wizard.product_id.price + sum(wizard.topping_ids.mapped('price')))

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
