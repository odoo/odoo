# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
import math
import hashlib
import random

from openerp import models, fields, api


class SaleApplicability(models.Model):
    _name = 'sale.applicability'
    _description = "Sales Coupon Applicability"

    partner_id = fields.Many2one('res.partner', string="Limit to a single customer", help="Coupon program will work only for the perticular selected customer")
    date_from = fields.Date("Date From", help="Date on which coupon will get activated")
    date_to = fields.Date("Date To", help="Date after which coupon will get deactivated")
    validity_type = fields.Selection(
        [('day', 'Day(s)'),
         ('week', 'Week(s)'),
         ('month', 'Month(s)'),
         ('year', 'Year(s)'),
         ], string='Validity Type', required=True, default='day',
        help="Validity Type can be based on either day, month, week or year.")
    validity_duration = fields.Integer("Validity Duration", help="Validity duration can be set according to validity type")
    expiration_use = fields.Integer("Expiration use", default="1", help="Number of Times coupon can be Used")
    purchase_type = fields.Selection([('product', 'Product'), ('category', 'Category'),
                                      ('amount', 'Amount')], string="Type", required=True, default="product")
    product_id = fields.Many2one('product.product', string="Product")
    product_category_id = fields.Many2one('product.category', string="Product Categoy")
    product_quantity = fields.Integer("Quantity", default=1)
    product_uom_id = fields.Many2one('product.uom', string="UoM", readonly=True)
    minimum_amount = fields.Float(string="Amount", help="Alteast amount, for that customer have to purchase to get the reward")
    applicability_tax = fields.Selection([('tax_included', 'Tax included'), ('tax_excluded', 'Tax excluded')], default="tax_excluded")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one("res.currency", readonly=True, default=lambda self: self.env.user.company_id.currency_id.id)

    @api.onchange('product_id')
    def get_uom_id(self):
        self.product_uom_id = self.product_id.product_tmpl.id.uom_id

    def get_expiration_date(self, start_date):
        if self.validity_type == 'day':
            return start_date + relativedelta(days=(self.duration))
        if self.validity_type == 'month':
            return start_date + relativedelta(months=self.duration)
        if self.validity_type == 'week':
            return start_date + relativedelta(days=(self.duration * 7))
        if self.validity_type == 'year':
            return start_date + relativedelta(months=(self.duration * 12))


class SaleReward(models.Model):
    _name = 'sale.reward'
    _description = "Sales Coupon Rewards"

    reward_type = fields.Selection([('product', 'Product'),
                                    ('discount', 'Discount'),
                                    ('coupon', 'Coupon')], string="Free gift", help="Type of reward to give to customer", default="product", required=True)
    reward_shipping_free = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Free Shipping", default="no", help="Shipment of the order is free or not")
    reward_product_product_id = fields.Many2one('product.product', string="Product")
    reward_quantity = fields.Integer(string="Quantity", default=1)
    reward_product_uom_id = fields.Many2one('product.uom', string="UoM", readonly=True)
    reward_gift_coupon_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    reward_discount_type = fields.Selection([('no', 'No'), ('percentage', 'Percentage'),
                                             ('amount', 'Amount')], string="Apply a discount", default="no")
    reward_discount_percentage = fields.Float("Discount", help='The discount in percentage')
    reward_discount_amount = fields.Float("Discount", help='The discount in fixed amount')
    reward_discount_on = fields.Selection([('cart', 'On cart'), ('cheapest_product', 'On cheapest product'),
                                           ('specific_product', 'On specific product')], string="Discount On", default="cart")
    reward_discount_on_product_id = fields.Many2one('product.product', string="Product")
    reward_tax = fields.Selection([('tax_included', 'Tax included'),
                                   ('tax_excluded', 'Tax excluded')], string="Tax", default="tax_excluded")
    reward_partial_use = fields.Selection([('yes', 'Yes'), ('no', 'No')], default="no", string="Partial use", help="The reward can be used partially or not")


class SaleCoupon(models.Model):
    _name = 'sale.coupon'
    _description = "Sales Coupon"

    program_id = fields.Many2one('sale.couponprogram', string="Program")
    coupon_code = fields.Char(string="Coupon Code",
                              default=lambda self: 'SC' + (hashlib.sha1(str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
                              required=True, readonly=True, help="Coupon Code")
    nbr_used = fields.Integer(string="Number of times coupon is used")
    nbr_uses = fields.Integer(string="Number of times coupon can be use")
    order_line_id = fields.One2many('sale.order.line', 'coupon_id', string="Sale order line")
    state = fields.Selection([
                             ('new', 'New'),
                             ('used', 'Used'),
                             ('expired', 'Expired')],
                             'Status', required=True, copy=False, track_visibility='onchange',
                             default='new')
    ean13 = fields.Char(string="Bar Code")
    origin = fields.Char(string="Origin", help="Coupon is originated from")
    origin_order_id = fields.Many2one('sale.order', string='Order Reference', readonly=True, help="The Sales order id from which coupon is generated")
    reward_name = fields.Char(string="Reward", help="Reward on coupon")


class SaleCouponProgram(models.Model):
    _name = 'sale.couponprogram'
    _description = "Sales Coupon Program"
    _inherits = {'sale.applicability': 'applicability_id', 'sale.reward': 'reward_id'}
    name = fields.Char(help="Program name", required=True)
    program_code = fields.Char(string='Coupon Code',
                               default=lambda self: 'SC' +
                                                    (hashlib.sha1(
                                                     str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
                               required=True, readonly=True, help="Coupon Code", store=True)
    program_type = fields.Selection([('apply_immediately', 'Apply Immediately'), ('public_unique_code',
                                     'Public Unique Code'), ('generated_coupon', 'Generated Coupon')],
                                    string="Program Type", help="The type of the coupon program", required=True, default="apply_immediately")
    active = fields.Boolean(string="Active", default=True, help="Coupon program is active or inactive")
    program_sequence = fields.Integer(string="Sequence", help="According to sequence, one rule is selected from multiple defined rules to apply")
    coupon_ids = fields.One2many('sale.coupon', 'program_id', string="Coupon Id")
    applicability_id = fields.Many2one('sale.applicability', string="Applicability Id", ondelete='cascade', required=True)
    reward_id = fields.Many2one('sale.reward', string="Reward", ondelete='cascade', required=True)

    @api.onchange('program_type')
    def generate_public_unique_code(self):
        if self.program_type == 'public_unique_code':
            coupon = self.env['sale.coupon'].create({'program_id': self.id})
            self.program_code = coupon.coupon_code

    def generate_coupon(self):
        pass


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")
    coupon_program_line_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    # @api.multi
    # def button_confirm(self):
    #     res = super(SaleOrderLine, self).button_confirm()
    #     if self[0].order_id.coupon_program_id:
    #         coupon = self.env['sale.coupon'].create({'program_id': self[0].order_id.coupon_program_id.id})
    #         print "------coupon ---", coupon['coupon_code']
    #     return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    typed_code = fields.Char(string="Coupon", help="Please enter the coupon code")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    def _search_rewards(self, domain=[]):
        find_reward_programs = self.env['sale.couponprogram'].search(domain + [
            '|',
            '&', ('purchase_type', '=', 'amount'), '|',
            '&', ('reward_tax', '=', 'tax_excluded'), ('minimum_amount', '<=', self.amount_total),
            '&', ('reward_tax', '=', 'tax_included'), ('minimum_amount', '<=', self.amount_untaxed),
            '|'] +
            ['&', ('purchase_type', '=', 'product')] + self._make_product_domain()
            + ['&', ('purchase_type', '=', 'category')] + self._make_product_category_domain()
        )
        return find_reward_programs

    def _make_product_domain(self):
        so_line_group = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
        domain = []
        for line in so_line_group:
            if not domain:
                domain = ['&', ('product_id', '=', line['product_id'][0]), ('product_quantity', '<=', line['product_uom_qty'])]
            else:
                domain = ['|'] + domain + ['&', ('product_id', '=', line['product_id'][0]), ('product_quantity', '<=', line['product_uom_qty'])]
        return domain

    def _make_product_category_domain(self):
        so_line_group = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
        domain = []
        for line in so_line_group:
            category = self.env['product.template'].search([('product_variant_ids', '=', line['product_id'][0])]).categ_id.id
            if not domain:
                domain = ['&', ('product_category_id', '=', category), ('product_quantity', '<=', line['product_uom_qty'])]
            else:
                domain = ['|'] + domain + ['&', ('product_category_id', '=', category), ('product_quantity', '<=', line['product_uom_qty'])]
        return domain

    def _process_rewards(self, reward_programs):
        for reward_program in reward_programs:
            reward_qty = self._compute_reward_quantity(reward_program)
            getattr(self, '_process_reward_' + reward_program.reward_type)(reward_program.reward_id, reward_qty)

    def _compute_reward_quantity(self, program):
        so_line_group = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
        #result = dict((data['product_id'][0], data['product_uom_qty']) for data in so_line_group)
        if program.purchase_type == 'product':
            for line in so_line_group:
                if line['product_id'][0] == program.product_id.id:
                    return math.floor((line['product_uom_qty']/program.product_quantity))
        if program.purchase_type == 'amount':
            return math.floor(self.amount_total/program.minimum_amount)
        if program.purchase_type == 'category':
            #to get total product qty of applicable category
            product_qty = 0
            for line in self.order_line:
                category = self.env['product.template'].search([('product_variant_ids', '=', line.product_id.id)]).categ_id.id
                if category == program.product_category_id.id:
                    product_qty = product_qty + line.product_uom_qty
            return math.floor((product_qty/program.product_quantity))

    def _process_reward_product(self, reward, quantity):
        program = self.env['sale.couponprogram'].search([('reward_id', '=', reward.id)])
        so_line_group = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
        #result = dict((data['product_id'][0], data['product_uom_qty']) for data in so_line_group)
        for line in self.order_line:
            #print "---------------", result.get(line.product_id)
            if line.product_id == reward.reward_product_product_id:
                for line_group in so_line_group:
                    if line_group['product_id'][0] == line.product_id.id:
                        line.update({'product_uom_qty': (line.product_uom_qty + (reward.reward_quantity * quantity))})
                        self._create_so_reward_line(line.price_unit, reward.reward_quantity * quantity)
                return True
        price_unit = self.env['product.template'].search([('product_variant_ids', '=', reward.reward_product_product_id.id)]).list_price
        reward_line = self._create_so_reward_product_line(reward.reward_product_product_id, price_unit, reward.reward_quantity * quantity)
        reward_line.update({'coupon_program_line_id': program.id})
        self._create_so_reward_line(price_unit, reward.reward_quantity * quantity)
        return True

    def _process_reward_discount(self, reward, quantity):
        if reward.reward_discount_type == 'amount':
            self._create_so_reward_line(reward.reward_discount_amount, quantity)
        if reward.reward_discount_type == 'percentage':
            getattr(self, '_process_reward_percentage_on_' + reward.reward_discount_on)(reward, quantity)

    def _process_reward_copuon(self, reward, quantity):
        pass

    def _process_reward_percentage_on_cart(self, reward, quantity):
        self._create_so_reward_line(self.amount_total * (reward.reward_discount_percentage / 100), quantity)

    def _process_reward_percentage_on_specific_product(self, reward, quantity):
        program = self.env['sale.couponprogram'].search([('reward_id', '=', reward.id)])
        for line in self.order_line:
            if line.product_id.id == reward.reward_discount_on_product_id.id:
                line.update({'product_uom_qty': line.product_uom_qty + (reward.reward_quantity * quantity)})
                self._create_so_reward_line(line.price_unit * (reward.reward_discount_percentage) / 100, quantity)
                return True
        price_unit = self.env['product.template'].search([('product_variant_ids', '=', reward.reward_discount_on_product_id.id)]).list_price
        reward_product_line = self._create_so_reward_product_line(reward.reward_discount_on_product_id, price_unit, quantity)
        reward_product_line.update({'coupon_program_line_id': program.id})
        self._create_so_reward_line(price_unit * (reward.reward_discount_percentage) / 100, quantity)
        return True

    def _process_reward_percentage_on_cheapest_product(self, reward, quantity):
        list_of_unit_price = []
        for line in self.order_line:
            list_of_unit_price.append(line.price_unit)
        self._create_so_reward_line((min(list_of_unit_price) * (reward.reward_discount_percentage) / 100), quantity)
        return True

    def _create_so_reward_product_line(self, product, unit_price, quantity):
        order_line_obj = self.env['sale.order.line']
        return order_line_obj.create({'product_id': product.id,
                                      'order_id': self.id,
                                      'price_unit': unit_price,
                                      'product_uom_qty': quantity})

    def _create_so_reward_line(self, amount, quantity):
        order_line_obj = self.env['sale.order.line']
        #if so already have product
        for line in self.order_line:
            if line.product_id == self.env.ref('website_sale_coupon.product_product_reward').id:
                    return line.update({'product_uom_qty': line.product_uom_qty + quantity,
                                        'price_unit': line.price_unit - amount})
        return order_line_obj.create({'product_id': self.env.ref('website_sale_coupon.product_product_reward').id,
                                      'order_id': self.id,
                                      'price_unit': -amount,
                                      'product_uom_qty': quantity})

    def _delete_so_reward_line(self, sale_order_line):
        sale_order_line.unlink()

    def _delete_so_reward_product_line(self, sale_order_line):
        sale_order_line.unlink()

    @api.multi
    def apply_immediately_reward(self):
        for order_line in self.order_line:
            if order_line.coupon_program_line_id:
                self._delete_so_reward_product_line(order_line)
                continue
            if order_line.product_id.id == self.env.ref('website_sale_coupon.product_product_reward').id:
                self._delete_so_reward_line(order_line)
        for sale_order in self:
            if sale_order.order_line:
                programs = sale_order._search_rewards([('program_type', '=', 'apply_immediately')])
                print "-----", programs
                sale_order._process_rewards(programs)

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.apply_immediately_reward()
        return res

    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self.apply_immediately_reward()
        return res


class GenerateManualCoupon(models.TransientModel):
    _name = 'sale.manual.coupon'

    nbr_coupons = fields.Integer("Number of coupons")
