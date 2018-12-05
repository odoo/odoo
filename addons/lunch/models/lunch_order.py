# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp


class LunchOrder(models.Model):
    """
    A lunch order contains one or more lunch order line(s). It is associated to a user for a given
    date.
    """
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'date desc'

    def _default_previous_order_ids(self):
        prev_order = self.env['lunch.order.line'].search([('user_id', '=', self.env.uid), ('product_id.active', '!=', False)], limit=20, order='id desc')
        # If we return return prev_order.ids, we will have duplicates (identical orders).
        # Therefore, this following part removes duplicates based on product_id and note.
        return list({
            (order.product_id, order.note): order.id
            for order in prev_order
        }.values())

    user_id = fields.Many2one('res.users', 'User', readonly=True,
                              states={'new': [('readonly', False)]},
                              default=lambda self: self.env.uid)
    date = fields.Date('Date', required=True, readonly=True,
                       states={'new': [('readonly', False)]},
                       default=fields.Date.context_today)
    order_line_ids = fields.One2many('lunch.order.line', 'order_id', 'Products',
                                     readonly=True, copy=True,
                                     states={'new': [('readonly', False)], False: [('readonly', False)]})
    total = fields.Float(compute='_compute_total', string="Total", store=True)
    state = fields.Selection([('new', 'New'),
                              ('ordered', 'Ordered'),
                              ('confirmed', 'Received'),
                              ('cancelled', 'Cancelled')],
                             'Status', readonly=True, index=True, copy=False, default='new')
    company_id = fields.Many2one('res.company', related='user_id.company_id', store=True, readonly=False)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, store=True)
    cash_move_balance = fields.Monetary(compute='_compute_cash_move_balance', multi='cash_move_balance')
    balance_visible = fields.Boolean(compute='_compute_cash_move_balance', multi='cash_move_balance')

    mail_sent = fields.Boolean('Mail Sent', readonly=True)
    supplier_ids = fields.Many2many('lunch.supplier', compute='_compute_supplier_ids', store=True)

    @api.depends('order_line_ids', 'order_line_ids.supplier_id', 'order_line_ids.product_id')
    def _compute_supplier_ids(self):
        for order in self:
            order.supplier_ids = order.mapped('order_line_ids.supplier_id')

    @api.depends('order_line_ids', 'order_line_ids.quantity', 'order_line_ids.price')
    def _compute_total(self):
        """
        get and sum the order lines' price
        """
        self.ensure_one()
        self.total = sum(
            orderline.price for orderline in self.order_line_ids)

    @api.multi
    def name_get(self):
        return [(order.id, '%s %s' % (_('Lunch Order'), '#%d' % order.id)) for order in self]

    @api.depends('user_id')
    def _compute_cash_move_balance(self):
        self.ensure_one()
        domain = [('user_id', '=', self.user_id.id)]
        lunch_cash = self.env['lunch.cashmove'].read_group(domain, ['amount', 'user_id'], ['user_id'])
        if lunch_cash:
            self.cash_move_balance = lunch_cash[0]['amount']
        self.balance_visible = (self.user_id == self.env.user) or self.user_has_groups('lunch.group_lunch_manager')

    @api.constrains('date')
    def _check_date(self):
        """
        Prevents the user to create an order in the past
        """
        self.ensure_one()
        date_order = self.date
        date_today = fields.Date.context_today(self)
        if date_order < date_today:
            raise ValidationError(_('The date of your order is in the past.'))

    def action_order(self):
        for order in self:
            for line in order.order_line_ids:
                self.env['lunch.cashmove'].sudo().create({
                    'user_id': line.user_id.id,
                    'amount': -line.price,
                    'description': line.product_id.name,
                    'order_line_id': line.id,
                    'state': 'order',
                    'date': line.date,
                })

        self.mapped('order_line_ids').write({'state': 'ordered'})
        self.write({'state': 'ordered'})

    def action_confirm(self, supplier=None):
        for order in self:
            if supplier:
                order.order_line_ids.filtered(lambda line: line.state == 'ordered' and line.supplier_id == supplier).write({'state': 'confirmed'})
            else:
                order.order_line_ids.filtered(lambda line: line.state == 'ordered').write({'state': 'confirmed'})
            order.write({'state': 'confirmed',
                         'mail_sent': True})

    def action_cancel(self):
        for order in self:
            # RLI FIXME maybe we don't need to filter
            order.order_line_ids.filtered(lambda line: line.state != 'confirmed').action_cancel()
            order.write({'state': 'cancelled'})


class LunchOrderLine(models.Model):
    _name = 'lunch.order.line'
    _description = 'Lunch Order Line'
    _order = 'date desc, id desc'

    name = fields.Char(related='product_id.name', string="Product Name", readonly=True)
    order_id = fields.Many2one('lunch.order', 'Order', ondelete='cascade', required=True)
    topping_ids = fields.Many2many('lunch.topping', string='Toppings')
    product_id = fields.Many2one('lunch.product', string="Product", required=True)
    category_id = fields.Many2one('lunch.product.category', string='Product Category',
                                  related='product_id.category_id', readonly=True, store=True)
    date = fields.Date(string='Date', related='order_id.date', readonly=True, store=True)
    supplier_id = fields.Many2one('lunch.supplier', string='Vendor', related='product_id.supplier_id',
                               readonly=True, store=True, index=True)
    user_id = fields.Many2one('res.users', string='User', related='order_id.user_id',
                              readonly=True, store=True)
    note = fields.Text('Note')
    price = fields.Float('Total Price', compute='_compute_total_price', readonly=True, store=True,
                         digits=dp.get_precision('Account'))
    state = fields.Selection([('new', 'New'),
                              ('ordered', 'Ordered'),
                              ('confirmed', 'Received'),
                              ('cancelled', 'Cancelled')],
                             'Status', readonly=True, index=True, default='new')
    cashmove = fields.One2many('lunch.cashmove', 'order_line_id', 'Cash Move')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=False)
    quantity = fields.Float('Quantity', required=True, default=1)

    @api.depends('topping_ids', 'product_id', 'quantity')
    def _compute_total_price(self):
        for line in self:
            line.price = line.quantity * (line.product_id.price + sum(line.topping_ids.mapped('price')))

    def update_quantity(self, increment):
        for line in self:
            old_cost = line.price
            line.quantity += increment
            new_cost = line.price
            if new_cost - old_cost > self.env['lunch.cashmove'].get_wallet_balance(line.user_id):
                raise UserError(_('Your wallet does not contain enough money to order that.'
                                  'To add some money to your wallet, please contact your lunch manager.'))
            cashmove = self.env['lunch.cashmove'].search([('order_line_id', '=', line.id)], limit=1)
            if cashmove:
                cashmove.amount = -new_cost
            if line.quantity <= 0:
                order_id = line.order_id
                line.sudo().unlink()
                if not order_id.order_line_ids:
                    order_id.sudo().unlink()

    def action_confirm(self):
        self.write({'state': 'confirmed'})

        for order in self.mapped('order_id'):
            if all(line.state == 'confirmed' for line in order.order_line_ids):
                order.write({'state': 'confirmed', 'mail_sent': True})

    def action_cancel(self):
        for line in self:
            line.cashmove.sudo().unlink()

        self.write({'state': 'cancelled'})
