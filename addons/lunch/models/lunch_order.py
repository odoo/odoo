# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LunchOrder(models.Model):
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'id desc'
    _display_name = 'product_id'

    name = fields.Char(related='product_id.name', string="Product Name", readonly=True)  # to remove
    topping_ids_1 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 1', domain=[('topping_category', '=', 1)])
    topping_ids_2 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 2', domain=[('topping_category', '=', 2)])
    topping_ids_3 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 3', domain=[('topping_category', '=', 3)])
    product_id = fields.Many2one('lunch.product', string="Product", required=True)
    category_id = fields.Many2one('lunch.product.category', string='Product Category',
                                  related='product_id.category_id', readonly=True, store=True)
    date = fields.Date('Order Date', required=True, readonly=True,
                       states={'new': [('readonly', False)]},
                       default=fields.Date.context_today)
    supplier_id = fields.Many2one('lunch.supplier', string='Vendor', related='product_id.supplier_id',
                               readonly=True, store=True, index=True)
    user_id = fields.Many2one('res.users', 'User', readonly=True,
                              states={'new': [('readonly', False)]},
                              default=lambda self: self.env.uid)
    note = fields.Text('Notes')
    price = fields.Float('Total Price', compute='_compute_total_price', readonly=True, store=True,
                         digits='Account')
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([('new', 'To Order'),
                              ('ordered', 'Ordered'),
                              ('confirmed', 'Received'),
                              ('cancelled', 'Cancelled')],
                             'Status', readonly=True, index=True, default='new')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, store=True)
    quantity = fields.Float('Quantity', required=True, default=1)

    display_toppings = fields.Text('Extras', compute='_compute_display_toppings', store=True)

    def init(self):
        self._cr.execute("""CREATE INDEX IF NOT EXISTS lunch_order_user_product_date ON %s (user_id, product_id, date)"""
            % self._table)

    @api.depends('topping_ids_1', 'topping_ids_2', 'topping_ids_3', 'product_id', 'quantity')
    def _compute_total_price(self):
        for line in self:
            line.price = line.quantity * (line.product_id.price + sum((line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3).mapped('price')))

    @api.depends('topping_ids_1', 'topping_ids_2', 'topping_ids_3')
    def _compute_display_toppings(self):
        for line in self:
            toppings = line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3
            line.display_toppings = ' + '.join(toppings.mapped('name'))

    def update_quantity(self, increment):
        for line in self.filtered(lambda line: line.state != 'confirmed'):
            if line.quantity <= -increment:
                # TODO: maybe unlink the order?
                line.active = False
            else:
                line.quantity += increment
        self._check_wallet()

    def _check_wallet(self):
        self.flush()
        for line in self:
            if self.env['lunch.cashmove'].get_wallet_balance(line.user_id) < 0:
                raise ValidationError(_('Your wallet does not contain enough money to order that.'
                        'To add some money to your wallet, please contact your lunch manager.'))

    def action_order(self):
        self.write({'state': 'ordered'})
        self._check_wallet()

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
