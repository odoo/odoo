# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from datetime import date, datetime

import hashlib
import math
import random


from openerp import models, fields, api, _
from openerp.exceptions import MissingError


class SaleApplicability(models.Model):
    _name = 'sale.applicability'
    _description = "Sales Coupon Applicability"

    partner_id = fields.Many2one('res.partner', string="Limit to a single customer", help="Coupon program will work only for the perticular selected customer")
    date_from = fields.Date("Date From", help="Date on which coupon will get activated", default=fields.date.today())
    date_to = fields.Date("Date To", help="Date after which coupon will get deactivated", default=fields.date.today() + relativedelta(days=1))
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
            return start_date + relativedelta(days=(self.validity_duration))
        if self.validity_type == 'month':
            return start_date + relativedelta(months=self.validity_duration)
        if self.validity_type == 'week':
            return start_date + relativedelta(days=(self.validity_duration * 7))
        if self.validity_type == 'year':
            return start_date + relativedelta(months=(self.validity_duration * 12))


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
    # program_code = fields.Char(string='Coupon Code',
    #                            default=lambda self: 'SC' +
    #                                                 (hashlib.sha1(
    #                                                  str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
    #                            required=True,, help="Coupon Code", store=True)
    program_code = fields.Char(string="Program Code")
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

    # @api.onchange('program_type')
    # def generate_public_unique_code(self):
    #     if self.program_type == 'public_unique_code':
    #         coupon = self.env['sale.coupon'].create({'program_id': self.id})
    #         self.program_code = coupon.coupon_code

    def is_program_valid(self):
        if self.program_type == 'generated_coupon' or self.program_type == 'apply_immediately':
            if fields.date.today() <= self.applicability_id.get_expiration_date(datetime.strptime(self.create_date, "%Y-%m-%d %H:%M:%S").date()):
                return True
            else:
                print "<<<<<<<<< coupon has expired>>>>>>>>>>"
                return False
        if self.program_type == 'public_unique_code':
            if fields.date.today() <= datetime.strptime(self.date_to, "%Y-%m-%d").date():
                return True
            else:
                print "<<<<<<<<< coupon has expired>>>>>>>>>>"
                return False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    generated_from_line_id = fields.Many2one('sale.order.line')

    @api.multi
    def unlink(self):
        res = True
        try:
            reward_lines = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id.id in self.ids)
            if reward_lines:
                reward_lines.unlink()
            res = super(SaleOrderLine, self).unlink()
        except MissingError:
            pass
        return res

    @api.multi
    def apply_immediately_reward(self):
        programs = self._search_reward_programs([('program_type', '=', 'apply_immediately')])
        if programs:
            self.process_rewards(programs)
        return programs

    def _search_reward_programs(self, domain=[]):
        return self.env['sale.couponprogram'].search(domain + [
            '&', ('product_quantity', '<=', self.product_uom_qty),
            '|',
            '&', ('purchase_type', '=', 'product'), ('product_id', '=', self.product_id.id),
            '&', ('purchase_type', '=', 'category'), ('product_category_id', '=', self.product_id.categ_id.id)])

    @api.multi
    def process_rewards(self, programs):
        for program in programs:
            getattr(self, '_process_reward_' + program.reward_type)(program)

    def _create_discount_reward(self, program, qty, discount_amount):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward').id
        reward_lines = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id == self and x.product_id.id == reward_product_id and x.coupon_program_id == program)
        if discount_amount <= 0 and reward_lines:
            reward_lines.unlink()
        elif discount_amount > 0 and reward_lines:
            for reward_line in reward_lines:
                reward_line.with_context(noreward=True).write({'price_unit': -discount_amount, 'product_uom_qty': qty})
        if discount_amount > 0 and not reward_lines:
            if program.purchase_type == 'product':
                desc = _("Reward on ") + program.product_id.name
                if program.program_code:
                    desc = desc + " using code " + program.program_code
            if program.purchase_type == 'category':
                desc = _("Reward on category of ") + self.product_id.name
                if program.program_code:
                    desc = desc + " using code " + program.program_code
            vals = {
                'product_id': reward_product_id,
                'name': desc,
                'product_uom_qty': qty,
                'price_unit': -discount_amount,
                'order_id': self.order_id.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': self.id
            }
            self.with_context(noreward=True).create(vals)

    def _process_reward_product(self, program):
        #reward_product_id = self.env.ref('website_sale_coupon.product_product_reward').id
        product_lines = self.order_id.order_line.filtered(lambda x: x.product_id == program.reward_product_product_id)
        vals = self.product_id_change(self.order_id.pricelist_id.id, program.reward_product_product_id.id, program.reward_quantity,
                                      uom=program.reward_product_uom_id.id)['value']
        if product_lines:
            line = product_lines[0]
        if program.reward_product_product_id == program.product_id:
            to_reward_qty = math.floor(self.product_uom_qty / (program.product_quantity + program.reward_quantity))
            if not (to_reward_qty) and (line.product_uom_qty == program.product_quantity):
                product_qty = line.product_uom_qty + program.reward_quantity
                line.with_context(nocoupon=True).write({'product_uom_qty': product_qty})
                to_reward_qty = 1
        else:
            to_reward_qty = math.floor(self.product_uom_qty / program.product_quantity * program.reward_quantity)
        if not to_reward_qty:
            vals['price_unit'] = 0
        if not product_lines:
            vals['product_id'] = program.reward_product_product_id.id
            vals['product_uom_qty'] = to_reward_qty
            vals['order_id'] = self.order_id.id
            line = self.with_context(noreward=True).create(vals)
        else:
            if program.reward_product_product_id.id == line.product_id.id and \
               program.reward_product_product_id != program.product_id and line.product_uom_qty <= to_reward_qty:
                    line.with_context(noreward=True).write({'product_uom_qty': to_reward_qty})
        self._create_discount_reward(program, to_reward_qty, vals['price_unit'])

    def _process_reward_discount(self, program):
        discount_amount = 0
        if program.reward_discount_type == 'amount':
            discount_amount = program.reward_discount_amount
        elif program.reward_discount_type == 'percentage':
            if program.reward_discount_on == 'cart':
                discount_amount = self.order_id.amount_total * (program.reward_discount_percentage / 100)
            elif program.reward_discount_on == 'cheapest_product':
                    unit_prices = [x.price_unit for x in self.order_id.order_line if x.coupon_program_id.id is False]
                    discount_amount = (min(unit_prices) * (program.reward_discount_percentage) / 100)
            elif program.reward_discount_on == 'specific_product':
                #reward_qty = self.product_uom_qty / (program.product_quantity * program.reward_quantity)
                discount_amount = sum([x.price_unit * program.reward_discount_percentage / 100 for x in self.order_id.order_line if x.product_id == program.reward_discount_on_product_id])
        self._create_discount_reward(program, 1, discount_amount)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res._merage_product_line()
        if vals.get('order_line'):
            res.apply_immediately_reward()
        return res

    @api.multi
    def write(self, vals):
        if not self.is_reward_line_updated(vals):
            res = super(SaleOrder, self).write(vals)
            self._merage_product_line()
            if vals.get('order_line'):
                self.apply_immediately_reward()
            return res
        return True

    @api.multi
    def _merage_product_line(self):
        product_line = []
        line_to_remove = []
        for line in self.order_line:
            if line.product_id.id != self.env.ref('website_sale_coupon.product_product_reward').id:
                product_line = self.order_line.filtered(lambda x: x.product_id == line.product_id and x.id != line.id)
                for p_line in product_line:
                    if p_line and (line not in line_to_remove):
                        line.with_context(nocoupon=True).write({'product_uom_qty': line.product_uom_qty + p_line.product_uom_qty})
                        line_to_remove += p_line
        if line_to_remove:
            for line in line_to_remove:
                line.unlink()

    def is_reward_line_updated(self, vals):
        if vals.get('order_line'):
            for order_line in vals.get('order_line'):
                if order_line[2] is not False and self.order_line.browse(order_line[1]).product_id == self.env.ref('website_sale_coupon.product_product_reward'):
                    reward_line = self.order_line.filtered(lambda x: x.product_id == self.env.ref('website_sale_coupon.product_product_reward') and x.id == order_line[1])
                    order_line[2]['product_uom_qty'] = reward_line.product_uom_qty
                    return True

    def _search_reward_programs(self, domain=[]):
        return self.env['sale.couponprogram'].search(domain + [
            '&', ('purchase_type', '=', 'amount'), '|',
            '&', ('reward_tax', '=', 'tax_excluded'), ('minimum_amount', '<=', self.amount_total),
            '&', ('reward_tax', '=', 'tax_included'), ('minimum_amount', '<=', self.amount_untaxed)], limit=1, order="minimum_amount desc")

    def _check_current_reward_applicability(self, domain=[]):
        remove_reward_lines = []
        for order in self.filtered(lambda x: x.order_line is not False):
            programs = order._search_reward_programs(domain)
            if not programs:
                remove_reward_lines += order.order_line.filtered(lambda x: x.coupon_program_id.purchase_type == 'amount' and x.coupon_program_id.program_type == domain[0][2])
            #self.process_rewards(programs)
            for order_line in [x for x in order.order_line if not (x.coupon_program_id or x.generated_from_line_id)]:
                programs = order_line._search_reward_programs(domain)
                if programs:
                    if programs.reward_type == 'product' or (programs.reward_type == 'discount' and programs.reward_discount_on == 'specific_product'):
                        product_line = self.order_line.filtered(lambda x: x.product_id == programs.reward_product_product_id or x.product_id == programs.reward_discount_on_product_id)
                        if not product_line:
                            reward_line = self.order_line.filtered(lambda x: x.coupon_program_id == programs and x.generated_from_line_id == order_line)
                            remove_reward_lines += reward_line
                if not programs:
                    remove_reward_lines += self.order_line.filtered(lambda x: x.generated_from_line_id == order_line and x.coupon_program_id.id is not False and x.coupon_program_id.program_type == domain[0][2])
        for remove_line in remove_reward_lines:
            remove_line.with_context(nocoupon=True).unlink()

    def _check_for_free_shipping(self):
        free_shipping_product_line = self.order_line.filtered(lambda x: x.product_id.is_delivery_chargeble is True)
        if not free_shipping_product_line:
            return True
        product_line = free_shipping_product_line[0]
        delivery_charge_line = self.order_line.filtered(lambda x: x.product_id == self.env.ref('delivery.product_product_delivery'))
        if not delivery_charge_line:
            return True
        reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id == product_line)
        if reward_line.coupon_program_id.reward_shipping_free == 'yes':
            #reward_line.with_context(noreward=True).write({'price_unit': reward_line.price_unit + (-delivery_charge_line.price_unit)})
            if not self.order_line.filtered(lambda x: x.generated_from_line_id == reward_line):
                vals = {
                    'product_id': self.env.ref('website_sale_coupon.product_product_reward').id,
                    'name': "Free Shipping",
                    'product_uom_qty': 1,
                    'price_unit': -delivery_charge_line.price_unit,
                    'order_id': self.id,
                    'coupon_program_id': reward_line.coupon_program_id.id,
                    'generated_from_line_id': reward_line.id
                }
                reward_line.with_context(noreward=True).create(vals)

    @api.multi
    def apply_immediately_reward(self):
        for order in self.filtered(lambda x: x.order_line is not False):
            programs = order._search_reward_programs([('program_type', '=', 'apply_immediately')])
            if programs:
                self.process_rewards(programs)
            for order_line in [x for x in order.order_line if not (x.coupon_program_id or x.generated_from_line_id)]:
                order_line.apply_immediately_reward()
            self._check_current_reward_applicability([('program_type', '=', 'apply_immediately')])
            self._check_current_reward_applicability([('program_type', '=', 'public_unique_code')])
            self._check_current_reward_applicability([('program_type', '=', 'generated_coupon')])
            self._check_for_free_shipping()

    @api.multi
    def apply_coupon_reward(self, coupon_code):
        program = self.env['sale.couponprogram'].search([('program_code', '=', coupon_code)], limit=1)
        if not program:
            program = self.env['sale.coupon'].search([('coupon_code', '=', coupon_code)], limit=1).program_id
            if not program:
                print "<<<<<<<invalid coupon >>>>>>>>"
        if program.is_program_valid() and program.program_type != 'apply_immediately':
            if program.purchase_type == 'amount' and ((self.amount_total >= program.minimum_amount and program.reward_tax == 'tax_excluded') or
                                                     (self.amount_untaxed >= program.minimum_amount and program.reward_tax == 'tax_excluded')):
                reward_product_id = self.env.ref('website_sale_coupon.product_product_reward')
                reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id.id is False and x.product_id == reward_product_id)
                if not reward_line:
                    self.process_rewards(program)
            if program.purchase_type == 'product':
                for line in self.order_line.filtered(lambda x: x.product_id == program.product_id and x.product_uom_qty >= program.product_quantity):
                    reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id == line)
                    if not reward_line:
                        line.process_rewards(program)
            if program.purchase_type == 'category':
                for line in self.order_line.filtered(lambda x: x.product_id.categ_id == program.product_category_id and x.product_uom_qty >= program.product_quantity):
                    reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id == line)
                    if not reward_line:
                        line.process_rewards(program)

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
                    unit_prices = [x.price_unit for x in self.order_line if x.coupon_program_id.id is False]
                    discount_amount = (min(unit_prices) * (program.reward_discount_percentage) / 100)
            elif program.reward_discount_on == 'specific_product':
                discount_amount = sum([x.price_unit * program.reward_discount_percentage / 100 for x in self.order_line if x.product_id == program.reward_product_product_id])
        self._create_discount_reward(program, discount_amount)

    def _create_discount_reward(self, program, discount_amount):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward')
        reward_lines = self.order_line.filtered(lambda x: x.generated_from_line_id.id is False and x.product_id.id == reward_product_id.id and x.coupon_program_id == program)
        if discount_amount <= 0 and reward_lines:
            reward_lines.unlink()
        elif discount_amount > 0 and reward_lines:
            for reward_line in reward_lines:
                discount_amount += (-1) * reward_line.price_unit
                reward_line.with_context(noreward=True).write({'price_unit': -discount_amount})
        elif discount_amount > 0 and not reward_lines:
            desc = "Reward on amount"
            if program.program_code:
                desc = desc + " using code " + program.program_code
            vals = {
                'product_id': reward_product_id.id,
                'name': desc,
                'product_uom_qty': 1,
                'price_unit': -discount_amount,
                'order_id': self.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': False
            }
            self.order_line.with_context(noreward=True).create(vals)


class ProductProduct(models.Model):
    _inherit = "product.template"

    is_delivery_chargeble = fields.Boolean("Delivery chargeble")


class GenerateManualCoupon(models.TransientModel):
    _name = 'sale.manual.coupon'

    nbr_coupons = fields.Integer("Number of coupons")

    @api.multi
    def generate_coupon(self):
        program_id = self.env['sale.couponprogram'].browse(self._context.get('active_id'))
        sale_coupon = self.env['sale.coupon']
        for count in range(0, self.nbr_coupons):
            sale_coupon.create({'program_id': program_id.id, 'nbr_uses': 1})


class GetCouponCode(models.TransientModel):
    _name = 'sale.get.coupon'

    textbox_coupon_code = fields.Char("Coupon", required=True)

    @api.multi
    def process_coupon(self):
        sale_order_id = self.env['sale.order'].browse(self._context.get('active_ids'))
        sale_order_id.apply_coupon_reward(self.textbox_coupon_code)
