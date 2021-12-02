# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class LunchOrder(models.Model):
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'id desc'
    _display_name = 'product_id'

    name = fields.Char(related='product_id.name', string="Product Name", store=True, readonly=True)
    topping_ids_1 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 1', domain=[('topping_category', '=', 1)])
    topping_ids_2 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 2', domain=[('topping_category', '=', 2)])
    topping_ids_3 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 3', domain=[('topping_category', '=', 3)])
    product_id = fields.Many2one('lunch.product', string="Product", required=True)
    category_id = fields.Many2one(
        string='Product Category', related='product_id.category_id', store=True)
    date = fields.Date('Order Date', required=True, readonly=True,
                       states={'new': [('readonly', False)]},
                       default=fields.Date.context_today)
    supplier_id = fields.Many2one(
        string='Vendor', related='product_id.supplier_id', store=True, index=True)
    user_id = fields.Many2one('res.users', 'User', readonly=True,
                              states={'new': [('readonly', False)]},
                              default=lambda self: self.env.uid)
    lunch_location_id = fields.Many2one('lunch.location', default=lambda self: self.env.user.last_lunch_location_id)
    note = fields.Text('Notes')
    price = fields.Monetary('Total Price', compute='_compute_total_price', readonly=True, store=True)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([('new', 'To Order'),
                              ('ordered', 'Ordered'),
                              ('confirmed', 'Received'),
                              ('cancelled', 'Cancelled')],
                             'Status', readonly=True, index=True, default='new')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    quantity = fields.Float('Quantity', required=True, default=1)

    display_toppings = fields.Text('Extras', compute='_compute_display_toppings', store=True)

    product_description = fields.Html('Description', related='product_id.description')
    topping_label_1 = fields.Char(related='product_id.supplier_id.topping_label_1')
    topping_label_2 = fields.Char(related='product_id.supplier_id.topping_label_2')
    topping_label_3 = fields.Char(related='product_id.supplier_id.topping_label_3')
    topping_quantity_1 = fields.Selection(related='product_id.supplier_id.topping_quantity_1')
    topping_quantity_2 = fields.Selection(related='product_id.supplier_id.topping_quantity_2')
    topping_quantity_3 = fields.Selection(related='product_id.supplier_id.topping_quantity_3')
    image_1920 = fields.Image(compute='_compute_product_images')
    image_128 = fields.Image(compute='_compute_product_images')

    available_toppings_1 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    available_toppings_2 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    available_toppings_3 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    display_reorder_button = fields.Boolean(compute='_compute_display_reorder_button')

    @api.depends('product_id')
    def _compute_product_images(self):
        for line in self:
            line.image_1920 = line.product_id.image_1920 or line.category_id.image_1920
            line.image_128 = line.product_id.image_128 or line.category_id.image_128

    @api.depends('category_id')
    def _compute_available_toppings(self):
        for order in self:
            order.available_toppings_1 = bool(order.env['lunch.topping'].search_count([('supplier_id', '=', order.supplier_id.id), ('topping_category', '=', 1)]))
            order.available_toppings_2 = bool(order.env['lunch.topping'].search_count([('supplier_id', '=', order.supplier_id.id), ('topping_category', '=', 2)]))
            order.available_toppings_3 = bool(order.env['lunch.topping'].search_count([('supplier_id', '=', order.supplier_id.id), ('topping_category', '=', 3)]))

    @api.depends_context('show_reorder_button')
    @api.depends('state')
    def _compute_display_reorder_button(self):
        show_button = self.env.context.get('show_reorder_button')
        for order in self:
            order.display_reorder_button = show_button and order.state == 'confirmed'

    def init(self):
        self._cr.execute("""CREATE INDEX IF NOT EXISTS lunch_order_user_product_date ON %s (user_id, product_id, date)"""
            % self._table)

    def _extract_toppings(self, values):
        """
            If called in api.multi then it will pop topping_ids_1,2,3 from values
        """
        if self.ids:
            # TODO This is not taking into account all the toppings for each individual order, this is usually not a problem
            # since in the interface you usually don't update more than one order at a time but this is a bug nonetheless
            topping_1 = values.pop('topping_ids_1')[0][2] if 'topping_ids_1' in values else self[:1].topping_ids_1.ids
            topping_2 = values.pop('topping_ids_2')[0][2] if 'topping_ids_2' in values else self[:1].topping_ids_2.ids
            topping_3 = values.pop('topping_ids_3')[0][2] if 'topping_ids_3' in values else self[:1].topping_ids_3.ids
        else:
            topping_1 = values['topping_ids_1'][0][2] if 'topping_ids_1' in values else []
            topping_2 = values['topping_ids_2'][0][2] if 'topping_ids_2' in values else []
            topping_3 = values['topping_ids_3'][0][2] if 'topping_ids_3' in values else []

        return topping_1 + topping_2 + topping_3

    @api.constrains('topping_ids_1', 'topping_ids_2', 'topping_ids_3')
    def _check_topping_quantity(self):
        errors = {
            '1_more': _('You should order at least one %s'),
            '1': _('You have to order one and only one %s'),
        }
        for line in self:
            for index in range(1, 4):
                availability = line['available_toppings_%s' % index]
                quantity = line['topping_quantity_%s' % index]
                toppings = line['topping_ids_%s' % index].filtered(lambda x: x.topping_category == index)
                label = line['topping_label_%s' % index]

                if availability and quantity != '0_more':
                    check = bool(len(toppings) == 1 if quantity == '1' else toppings)
                    if not check:
                        raise ValidationError(errors[quantity] % label)

    @api.model
    def create(self, values):
        lines = self._find_matching_lines({
            **values,
            'toppings': self._extract_toppings(values),
        })
        if lines:
            # YTI FIXME This will update multiple lines in the case there are multiple
            # matching lines which should not happen through the interface
            lines.update_quantity(1)
            return lines[:1]
        return super().create(values)

    def write(self, values):
        merge_needed = 'note' in values or 'topping_ids_1' in values or 'topping_ids_2' in values or 'topping_ids_3' in values

        if merge_needed:
            lines_to_deactivate = self.env['lunch.order']
            for line in self:
                # Only write on topping_ids_1 because they all share the same table
                # and we don't want to remove all the records
                # _extract_toppings will pop topping_ids_1, topping_ids_2 and topping_ids_3 from values
                # This also forces us to invalidate the cache for topping_ids_2 and topping_ids_3 that
                # could have changed through topping_ids_1 without the cache knowing about it
                toppings = self._extract_toppings(values)
                self.invalidate_cache(['topping_ids_2', 'topping_ids_3'])
                values['topping_ids_1'] = [(6, 0, toppings)]
                matching_lines = self._find_matching_lines({
                    'user_id': values.get('user_id', line.user_id.id),
                    'product_id': values.get('product_id', line.product_id.id),
                    'note': values.get('note', line.note or False),
                    'toppings': toppings,
                })
                if matching_lines:
                    lines_to_deactivate |= line
                    matching_lines.update_quantity(line.quantity)
            lines_to_deactivate.write({'active': False})
            return super(LunchOrder, self - lines_to_deactivate).write(values)
        return super().write(values)

    @api.model
    def _find_matching_lines(self, values):
        domain = [
            ('user_id', '=', values.get('user_id', self.default_get(['user_id'])['user_id'])),
            ('product_id', '=', values.get('product_id', False)),
            ('date', '=', fields.Date.today()),
            ('note', '=', values.get('note', False)),
        ]
        toppings = values.get('toppings', [])
        return self.search(domain).filtered(lambda line: (line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3).ids == toppings)

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

    def add_to_cart(self):
        """
            This method currently does nothing, we currently need it in order to
            be able to reuse this model in place of a wizard
        """
        # YTI FIXME: Find a way to drop this.
        return True

    def _check_wallet(self):
        self.flush()
        for line in self:
            if self.env['lunch.cashmove'].get_wallet_balance(line.user_id) < 0:
                raise ValidationError(_('Your wallet does not contain enough money to order that. To add some money to your wallet, please contact your lunch manager.'))

    def action_order(self):
        for order in self:
            if not order.supplier_id.available_today:
                raise UserError(_('The vendor related to this order is not available today.'))
        if self.filtered(lambda line: not line.product_id.active):
            raise ValidationError(_('Product is no longer available.'))
        self.write({
            'state': 'ordered',
        })
        for order in self:
            order.lunch_location_id = order.user_id.last_lunch_location_id
        self._check_wallet()

    def action_reorder(self):
        self.ensure_one()
        if not self.supplier_id.available_today:
            raise UserError(_('The vendor related to this order is not available today.'))
        self.copy({
            'date': fields.Date.context_today(self),
            'state': 'ordered',
        })
        action = self.env['ir.actions.act_window']._for_xml_id('lunch.lunch_order_action')
        return action

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'ordered'})
