# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class LunchOrderWizard(models.TransientModel):
    _name = 'lunch.order.temp'
    _description = 'Lunch Order Temp'

    def _default_order_line(self):
        line_id = self.env.context.get('line_id')

        if line_id:
            last_time_ordered = self.env['lunch.order'].browse(line_id)
        else:
            last_time_ordered = self.env['lunch.order'].search([('product_id', '=', self.env.context.get('default_product_id', 0)),
                                                                ('user_id', '=', self.env.context.get('default_user_id', self.env.user.id))],
                                                                order="date desc, id desc", limit=1)
        return last_time_ordered

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    product_id = fields.Many2one('lunch.product', string='Product')
    product_description = fields.Text('Description', related='product_id.description')
    product_name = fields.Char('Product Name', related='product_id.name')
    product_category = fields.Many2one('lunch.product.category', related='product_id.category_id')
    topping_label_1 = fields.Char(related='product_id.category_id.topping_label_1')
    topping_label_2 = fields.Char(related='product_id.category_id.topping_label_2')
    topping_label_3 = fields.Char(related='product_id.category_id.topping_label_3')
    topping_quantity_1 = fields.Selection(related='product_id.category_id.topping_quantity_1')
    topping_quantity_2 = fields.Selection(related='product_id.category_id.topping_quantity_2')
    topping_quantity_3 = fields.Selection(related='product_id.category_id.topping_quantity_3')
    topping_ids_1 = fields.Many2many('lunch.topping', 'lunch_order_temp_topping', 'order_id', 'topping_id', string="Extra Garniture",
                                   domain="[('category_id', '=', product_category), ('topping_category', '=', 1)]",
                                   default=lambda self: self._default_order_line().topping_ids_1)
    topping_ids_2 = fields.Many2many('lunch.topping', 'lunch_order_temp_topping', 'order_id', 'topping_id', string="Extra Garniture 2",
                                     domain="[('category_id', '=', product_category), ('topping_category', '=', 2)]",
                                     default=lambda self: self._default_order_line().topping_ids_2)
    topping_ids_3 = fields.Many2many('lunch.topping', 'lunch_order_temp_topping', 'order_id', 'topping_id', string="Extra Garniture 3",
                                     domain="[('category_id', '=', product_category), ('topping_category', '=', 3)]",
                                     default=lambda self: self._default_order_line().topping_ids_3)

    available_toppings_1 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    available_toppings_2 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    available_toppings_3 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')

    image_1920 = fields.Image(related='product_id.image_1920')
    image_128 = fields.Image(related='product_id.image_128')

    quantity = fields.Float('Quantity', default=1)
    price_total = fields.Float('Total Price', compute='_compute_price_total')
    note = fields.Text('Special Instructions', default=lambda self: self._default_order_line().note)

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)
    edit = fields.Boolean('Edit Mode', default=lambda self: bool(self.env.context.get('line_id')))

    @api.depends('product_id')
    def _compute_available_toppings(self):
        for wizard in self:
            wizard.available_toppings_1 = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id), ('topping_category', '=', 1)]))
            wizard.available_toppings_2 = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id), ('topping_category', '=', 2)]))
            wizard.available_toppings_3 = bool(wizard.env['lunch.topping'].search_count([('category_id', '=', wizard.product_category.id), ('topping_category', '=', 3)]))

    @api.constrains('topping_ids_1', 'topping_ids_2', 'topping_ids_3')
    def _check_topping_quantity(self):
        errors = {
            '1_more': _('You should order at least one %s'),
            '1': _('You have to order one and only one %s'),
        }
        for wizard in self:
            for index in range(1, 4):
                availability = wizard['available_toppings_%s' % index]
                quantity = wizard['topping_quantity_%s' % index]
                toppings = wizard['topping_ids_%s' % index].filtered(lambda x: x.topping_category == index)
                label = wizard['topping_label_%s' % index]

                if availability and quantity != '0_more':
                    check = bool(len(toppings) == 1 if quantity == '1' else toppings)
                    if not check:
                        raise ValidationError(errors[quantity] % label)

    @api.depends('product_id', 'topping_ids_1', 'topping_ids_2', 'topping_ids_3', 'quantity')
    def _compute_price_total(self):
        for wizard in self:
            wizard.price_total = wizard.quantity * (wizard.product_id.price +
                                                    sum((wizard.topping_ids_1 | wizard.topping_ids_2 | wizard.topping_ids_3).mapped('price')))

    def _get_matching_lines(self):
        domain = [('user_id', '=', self.user_id.id), ('product_id', '=', self.product_id.id), ('date', '=', fields.Date.today()), ('note', '=', self._get_note())]
        lines = self.env['lunch.order'].search(domain)
        return lines.filtered(lambda line: (line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3) == self.topping_ids_1)

    def _get_note(self):
        """
            returns self.note, but make sure that if it is an empty string it becomes False
        """
        return self.note if self.note else False

    def add_to_cart(self):
        self.ensure_one()
        line_id = self.env.context.get('line_id')

        matching_line = False
        matching_lines = self._get_matching_lines()

        if matching_lines:
            matching_line = matching_lines[0]
            quantity = 1

            if matching_line.id != line_id:
                if self.edit:
                    line = self.env['lunch.order'].browse(line_id)
                    quantity = line.quantity
                    line.sudo().unlink()
            else:
                quantity = 0

            matching_line.quantity += quantity
        else:
            if self.edit:
                line = self.env['lunch.order'].browse(line_id)

                line.topping_ids_1 = self.topping_ids_1
                line.topping_ids_2 = self.topping_ids_2
                line.topping_ids_3 = self.topping_ids_3
                line.note = self._get_note()
            else:
                self.env['lunch.order'].create({
                    'product_id': self.product_id.id,
                    'topping_ids_1': [(6, 0, self.topping_ids_1.ids)],
                    'topping_ids_2': [(6, 0, self.topping_ids_2.ids)],
                    'topping_ids_3': [(6, 0, self.topping_ids_3.ids)],
                    'quantity': self.quantity,
                    'note': self._get_note()
                })
