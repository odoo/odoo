# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError, ValidationError


class LunchOrderLineWizard(models.TransientModel):
    _name = 'lunch.order.line.temp'
    _description = 'Lunch Order Line Temp'

    def _default_order_line(self):
        last_time_ordered = self.env['lunch.order.line'].search([('product_id', '=', self.env.context.get('default_product_id', 0))],
                                                                order="date desc", limit=1)
        return last_time_ordered

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)

    product_id = fields.Many2one('lunch.product', string='Product ID')
    product_description = fields.Text('Description', related='product_id.description')
    product_name = fields.Char('Product', related='product_id.name')
    product_category = fields.Many2one('lunch.product.category', related='product_id.category_id')
    topping_label_1 = fields.Char(related='product_id.category_id.topping_label_1')
    topping_label_2 = fields.Char(related='product_id.category_id.topping_label_2')
    topping_label_3 = fields.Char(related='product_id.category_id.topping_label_3')
    topping_quantity_1 = fields.Selection(related='product_id.category_id.topping_quantity_1')
    topping_quantity_2 = fields.Selection(related='product_id.category_id.topping_quantity_2')
    topping_quantity_3 = fields.Selection(related='product_id.category_id.topping_quantity_3')
    topping_ids = fields.Many2many('lunch.topping', string="Extra Garniture", domain="[('category_id', '=', product_category), ('label', '=', 1)]",
                                   default=lambda self: self._default_order_line().topping_ids)
    topping_ids_2 = fields.Many2many('lunch.topping', string="Extra Garniture 2", domain="[('category_id', '=', product_category), ('label', '=', 2)]",
                                     default=lambda self: self._default_order_line().topping_ids_2)
    topping_ids_3 = fields.Many2many('lunch.topping', string="Extra Garniture 3", domain="[('category_id', '=', product_category), ('label', '=', 3)]",
                                     default=lambda self: self._default_order_line().topping_ids_3)

    available_toppings = fields.Boolean(help='Are toppings available for this product', compute='_compute_available_toppings')
    available_toppings_2 = fields.Boolean(help='Are toppings available for this product', compute='_compute_available_toppings')
    available_toppings_3 = fields.Boolean(help='Are toppings available for this product', compute='_compute_available_toppings')

    quantity = fields.Float('Quantity', default=1)
    price_total = fields.Float('Total Price', compute='_compute_price_total')
    note = fields.Text('Special Instructions', default=lambda self: self._default_order_line().note)

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)

    @api.depends('product_id')
    def _compute_available_toppings(self):
        for wizard in self:
            wizard.available_toppings = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id), ('label', '=', 1)]))
            wizard.available_toppings_2 = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id), ('label', '=', 2)]))
            wizard.available_toppings_3 = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id), ('label', '=', 3)]))

    @api.constrains('topping_ids', 'topping_ids_2', 'topping_ids_3')
    def _check_topping_quantity(self):
        errors = {
            '1_more': _('You should order at least one %s'),
            '1': _('You can only order one %s'),
        }
        for wizard in self:
            if wizard.available_toppings and wizard.topping_quantity_1 != '0_more':
                check = bool(len(wizard.topping_ids) == 1 if wizard.topping_quantity_1 == '1' else wizard.topping_ids)
                if not check:
                    raise ValidationError(errors[wizard.topping_quantity_1] % wizard.topping_label_1)
            if wizard.available_toppings_2 and wizard.topping_quantity_2 != '0_more':
                check = bool(len(wizard.topping_ids_2) == 1 if wizard.topping_quantity_2 == '1' else wizard.topping_ids_2)
                if not check:
                    raise ValidationError(errors[wizard.topping_quantity_2] % wizard.topping_label_2)
            if wizard.available_toppings_3 and wizard.topping_quantity_3 != '0_more':
                check = bool(len(wizard.topping_ids_3) == 1 if wizard.topping_quantity_3 == '1' else wizard.topping_ids_3)
                if not check:
                    raise ValidationError(errors[wizard.topping_quantity_3] % wizard.topping_label_3)

    @api.depends('product_id', 'topping_ids', 'topping_ids_2', 'topping_ids_3', 'quantity')
    def _compute_price_total(self):
        for wizard in self:
            wizard.price_total = wizard.quantity * (wizard.product_id.price +
                                                    sum((wizard.topping_ids | wizard.topping_ids_2 | wizard.topping_ids_3).mapped('price')))

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
                'note': self.note
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
