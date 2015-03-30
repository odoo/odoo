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

    @api.onchange('product_id')
    def get_uom_id(self):
        self.product_uom_id = self.product_id.product_tmpl_id.uom_id

    @api.onchange('program_type')
    def generate_public_unique_code(self):
        if self.program_type == 'public_unique_code':
            coupon = self.env['sale.coupon'].create({'program_id': self.id})
            self.program_code = coupon.coupon_code


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    generated_from_line_id = fields.Many2one('sale.order.line')

    @api.multi
    def write(self, vals):
        print "in line write"
        res = super(SaleOrderLine, self).write(vals)
        if self.env.context.get('noreward'):
            return res
        if not (vals.get('coupon_program_id') or vals.get('generated_from_line_id')):
            self.apply_immediately_reward()
        return res

    @api.multi
    def unlink(self):
        reward_lines = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id.id == self.id)
        if reward_lines:
            reward_lines.unlink()
        return super(SaleOrderLine, self).unlink()

    @api.model
    def create(self, vals):
        res = super(SaleOrderLine, self).create(vals)
        if self._context.get('noreward'):
            return res
        if not (vals.get('coupon_program_id') or vals.get('generated_from_line_id')):
            res.apply_immediately_reward()
        return res

    @api.multi
    def apply_immediately_reward(self):
        remove_reward_lines = []
        for order_line in self.order_id.order_line.filtered(lambda x: x.coupon_program_id != False):
            programs = order_line._search_reward_programs([('program_type', '=', 'apply_immediately')])
            print "====programs", programs
            if not programs:
                remove_reward_lines += self.order_id.order_line.filtered(lambda x: x.generated_from_line_id == order_line.id and x.coupon_program_id is not False)
            self.process_rewards(programs)
        if remove_reward_lines:
            self.env['sale.order.line'].unlink(remove_reward_lines)

    def _search_reward_programs(self, domain=[]):
        return self.env['sale.couponprogram'].search(domain + [
            '&', ('product_quantity', '<=', self.product_uom_qty),
            '|',
            '&', ('purchase_type', '=', 'product'), ('product_id', '=', self.product_id.id),
            '&', ('purchase_type', '=', 'category'), ('product_category_id', '=', self.product_id.categ_id.id)])

    @api.multi
    def process_rewards(self, programs):
        #@ensure_one
        for program in programs:
            #reward_qty = self._compute_reward_quantity()
            getattr(self, '_process_reward_' + program.reward_type)(program)

    def _create_discount_reward(self, program, discount_amount):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward').id
        reward_lines = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id == self and x.product_id.id == reward_product_id and x.coupon_program_id == program)
        if discount_amount <= 0 and reward_lines:
            reward_lines.unlink()
        elif discount_amount > 0 and reward_lines:
            for reward_line in reward_lines:
                #discount_amount = (-1) * reward_line.price_unit
                reward_line.with_context(noreward=True).write({'price_unit': -discount_amount})
        if discount_amount > 0 and not reward_lines:
            vals = {
                'product_id': reward_product_id,
                'product_uom_qty': 1,
                'price_unit': -discount_amount,
                'order_id': self.order_id.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': self.id
            }
            print "--------", vals
            self.with_context(noreward=True).create(vals)

    def _process_reward_product(self, program):
        #and x.product_uom.id == program.reward_product_uom_id
        product_lines = self.order_id.order_line.filtered(lambda x: x.product_id == program.reward_product_product_id)
        vals = self.product_id_change(self.order_id.pricelist_id.id, program.reward_product_product_id.id, program.reward_quantity,
                                      uom=program.reward_product_uom_id.id)['value']
        reward_qty = self.product_uom_qty / program.product_quantity * program.reward_quantity
        if not product_lines:
            vals['product_id'] = program.reward_product_product_id.id
            vals['product_uom_qty'] = reward_qty
            vals['order_id'] = self.order_id.id
            line = self.with_context(noreward=True).create(vals)
        else:
            line = product_lines[0]
            if line.product_uom_qty < reward_qty and program.reward_product_product_id.id == line.product_id.id:
                line.with_context(noreward=True).write({'product_uom_qty': reward_qty})
            if program.product_id == program.reward_product_product_id and program.reward_product_product_id.id == line.product_id.id:
                reward_updated_qty = line.product_uom_qty + (program.reward_quantity * reward_qty)
                line.with_context(noreward=True).write({'product_uom_qty': reward_updated_qty})
        self._create_discount_reward(program, reward_qty * vals['price_unit'])

    def _process_reward_discount(self, program):
        discount_amount = 0
        if program.reward_discount_type == 'amount':
            discount_amount = program.reward_discount_amount
        elif program.reward_discount_type == 'percentage':
            if program.reward_discount_on == 'cart':
                discount_amount = self.order_id.amount_total * (program.reward_discount_percentage / 100)
            elif program.reward_discount_on == 'cheapest_product':
                    unit_prices = [x.price_unit for x in self.order_id.order_line if x.coupon_program_id is False]
                    discount_amount = (min(unit_prices) * (program.reward_discount_percentage) / 100)
            elif program.reward_discount_on == 'specific_product':
                #reward_qty = self.product_uom_qty / (program.product_quantity * program.reward_quantity)
                discount_amount = sum([x.price_unit * program.reward_discount_percentage / 100 for x in self.order_id.order_line if x.product_id == program.reward_discount_on_product_id])
        self._create_discount_reward(program, discount_amount)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    typed_code = fields.Char(string="Coupon", help="Please enter the coupon code")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if vals.get('order_line'):
            res.apply_immediately_reward()
        return res

    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if vals.get('order_line'):
            self.apply_immediately_reward()
        return res

    def _search_reward_programs(self, domain=[]):
        return self.env['sale.couponprogram'].search(domain + [
            '&', ('purchase_type', '=', 'amount'), '|',
            '&', ('reward_tax', '=', 'tax_excluded'), ('minimum_amount', '<=', self.amount_total),
            '&', ('reward_tax', '=', 'tax_included'), ('minimum_amount', '<=', self.amount_untaxed)], limit=1, order="minimum_amount desc")

    @api.multi
    def apply_immediately_reward(self):
        remove_reward_lines = []
        for order in self.filtered(lambda x: x.order_line is not False):
            programs = order._search_reward_programs([('program_type', '=', 'apply_immediately')])
            print "-----programs", programs
            if not programs:
                print "programs not found"
                # x.generated_from_line_id == False and
                remove_reward_lines += order.order_line.filtered(lambda x: x.coupon_program_id.purchase_type == 'amount')
                if remove_reward_lines:
                    #self.env['sale.order.line'].unlink(remove_reward_lines)
                    for line in remove_reward_lines:
                        line.with_context(nocoupon=True).unlink()
            self.process_rewards(programs)

    @api.multi
    def process_rewards(self, programs):
        #@ensure_one
        for program in programs:
            getattr(self, '_process_reward_' + program.reward_type)(program)

    def _process_reward_product(self, program):
        product_lines = self.order_line.filtered(lambda x: x.product_id == program.reward_product_product_id and x.product_uom == program.reward_product_uom_id)
        vals = self.order_line.product_id_change(self.pricelist_id.id, program.reward_product_product_id.id, program.reward_quantity,
                                                 uom=program.reward_product_uom_id.id)['value']
        if not product_lines:
            vals['product_id'] = program.reward_product_product_id.id
            vals['product_uom_qty'] = program.reward_quantity
            vals['order_id'] = self.id
            line = self.order_line.with_context(noreward=True).create(vals)
        else:
            line = product_lines[0]
            qty = line.product_uom_qty
            line.with_context(noreward=True).write({'product_uom_qty': qty + program.reward_quantity})
        self._create_discount_reward(program, program.reward_quantity * vals['price_unit'])

    def _process_reward_discount(self, program):
        if program.reward_discount_type == 'amount':
            discount_amount = program.reward_discount_amount
        elif program.reward_discount_type == 'percentage':
            if program.reward_discount_on == 'cart':
                discount_amount = self.amount_total * (program.reward_discount_percentage / 100)
            elif program.reward_discount_on == 'cheapest_product':
                    unit_prices = [x.price_unit for x in self.order_line if x.coupon_program_id is False]
                    discount_amount = (min(unit_prices) * (program.reward_discount_percentage) / 100)
            elif program.reward_discount_on == 'specific_product':
                discount_amount = sum([x.price_subtotal * program.reward_discount_percentage / 100 for x in self.order_line if x.product_id == program.reward_product_product_id])
        self._create_discount_reward(program, discount_amount)

    def _create_discount_reward(self, program, discount_amount):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward')
        reward_lines = self.order_line.filtered(lambda x: x.generated_from_line_id == False and x.product_id.id == reward_product_id.id and x.coupon_program_id == program)
        if discount_amount <= 0 and reward_lines:
            reward_lines.unlink()
        elif discount_amount > 0 and reward_lines:
            for reward_line in reward_lines:
                discount_amount += (-1) * reward_line.price_unit
                reward_line.with_context(noreward=True).write({'price_unit': -discount_amount})
        elif discount_amount > 0 and not reward_lines:
            vals = {
                'product_id': reward_product_id.id,
                'product_uom_qty': 1,
                'price_unit': -discount_amount,
                'order_id': self.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': False
            }
            self.order_line.with_context(noreward=True).create(vals)


class GenerateManualCoupon(models.TransientModel):
    _name = 'sale.manual.coupon'

    nbr_coupons = fields.Integer("Number of coupons")
