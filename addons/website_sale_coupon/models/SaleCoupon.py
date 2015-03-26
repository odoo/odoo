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

    def generate_coupon(self):
        pass


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")
    coupon_program_line_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    generated_from_line_id = fields.Many2one('sale.order.line')

    def _process_coupon(self, sale_order_line):
        programs = sale_order_line.order_id.find_coupon_program(sale_order_line, [('program_type', '=', 'apply_immediately')])
        if programs is None:
            self._check_updated_line_applicability(sale_order_line)
            return True
        #Process rewards if program is found
        self[0].order_id._process_rewards(programs)

    def _check_updated_line_applicability(self, sale_order_line):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward').id
        order_lines = self.order_id.order_line
        #to update the reward with qty 0 if current qty of applicable product is changed
        #and is not satisfying the applicability
        for line in order_lines:
            if line.product_id.id == reward_product_id and line.generated_from_line_id.id == sale_order_line.id:
                line.with_context(nocoupon=True).write({'product_uom_qty': 0})
        #to update the reward qty if reward product qty is updated manually
        #i.e. if qty of cover is updated manualy
        for line in order_lines:
            program = line.coupon_program_line_id
            if line.product_id.id == reward_product_id:
                if (program.reward_product_product_id.id or program.reward_discount_on_product_id.id) == sale_order_line.product_id.id:
                    if sale_order_line.product_uom_qty < line.product_uom_qty:
                        line.with_context(nocoupon=True).write({'product_uom_qty': sale_order_line.product_uom_qty})
        #To check if updated line belongs to purchase type = category then check on whole cart
        #for the reward qty
        #i.e if coca cola = 2, reward = 2, pepsi = 2, then if I make the pepsi's qty 1 then reward
        #should caculated for remaining qty of that category
        for line in order_lines:
            program = line.coupon_program_line_id
            if (line.product_id.id == reward_product_id) and (program.purchase_type == 'category'):
                category_id = self.env['product.template'].search([('product_variant_ids', '=', sale_order_line.product_id.id)]).categ_id
                if program.product_category_id.id == category_id.id:
                    qty = self.order_id._compute_reward_quantity([line.id, program])
                    line.with_context(nocoupon=True).write({'product_uom_qty': qty * program.reward_quantity})

    @api.multi
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        #To stop the execution on confirm button click
        if self[0].order_id.state == 'draft':
            if self._context.get('nocoupon'):
                return res
            self._process_coupon(self)
        return res

    @api.model
    def create(self, vals):
        # print "-----in line", self, vals
        # order_id = self.env['sale.order'].browse([vals.get('order_id')])
        # for line in order_id.order_line:
        #     if line.product_id.id == vals.get('product_id'):
        #         line.with_context(nocoupon=True).write({'product_uom_qty': 2})
        res = super(SaleOrderLine, self).create(vals)
        if res._context.get('nocoupon'):
            return res
        res._process_coupon(res)
        return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    typed_code = fields.Char(string="Coupon", help="Please enter the coupon code")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    def apply_immediately_reward(self):
        if self.order_line:
            programs = self._search_rewards([('program_type', '=', 'apply_immediately')])
            if programs:
                self._process_rewards(programs)

    def _search_rewards(self, domain=[]):
        res = []
        CouponProgram = self.env['sale.couponprogram']
        reward_programs = CouponProgram.search(domain + [
            '&', ('purchase_type', '=', 'amount'), '|',
            '&', ('reward_tax', '=', 'tax_excluded'), ('minimum_amount', '<=', self.amount_total),
            '&', ('reward_tax', '=', 'tax_included'), ('minimum_amount', '<=', self.amount_untaxed)])
        if reward_programs:
            res.append((False, reward_programs))
            return res
        for sale_line in self.order_line:
            if sale_line.product_id.id != self.env.ref('website_sale_coupon.product_product_reward').id:
                reward_programs = CouponProgram.search(domain + ['|'] +
                                                                ['&', ('purchase_type', '=', 'product')] + self._make_product_domain(sale_line) +
                                                                ['&', ('purchase_type', '=', 'category')] + self._make_product_category_domain(sale_line))
                if reward_programs:
                    res.append((sale_line.id, reward_programs))
        if res:
            return res
        else:
            return False

    def _make_product_domain(self, so_line):
        return ['&', ('product_id', '=', so_line.product_id.id), ('product_quantity', '<=', so_line.product_uom_qty)]

    def _make_product_category_domain(self, so_line):
        category = self.env['product.template'].search([('product_variant_ids', '=', so_line.product_id.id)]).categ_id.id
        return ['&', ('product_category_id', '=', category), ('product_quantity', '<=', so_line.product_uom_qty)]

    def _process_rewards(self, reward_programs):
        for reward_program in reward_programs:
            reward_qty = self._compute_reward_quantity(reward_program)
            getattr(self, '_process_reward_' + reward_program[1].reward_type)(reward_program, reward_qty)

    def _compute_reward_quantity(self, reward_program):
        program = reward_program[1]
        if program.purchase_type == 'product':
            for sale_line in self.order_line:
                if sale_line.product_id.id == program.product_id.id:
                    return math.floor(sale_line.product_uom_qty/program.product_quantity)
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

    def _process_reward_product(self, reward_data, quantity):
        reward = reward_data[1].reward_id
        for line in self.order_line:
            if line.product_id == reward.reward_product_product_id:
                if reward_data[1].product_id.id == reward.reward_product_product_id.id:
                    line.with_context(nocoupon=True).write({'product_uom_qty': line.product_uom_qty + (reward.reward_quantity * quantity)})
                    # line.write({'product_uom_qty': line.product_uom_qty + (reward.reward_quantity * quantity)})
                elif line.product_uom_qty < quantity:
                    line.with_context(nocoupon=True).write({'product_uom_qty': quantity})
                self._create_so_reward_line(line.price_unit, reward.reward_quantity * quantity, reward_data)
                return True
        price_unit = self.env['product.template'].search([('product_variant_ids', '=', reward.reward_product_product_id.id)]).list_price
        self._create_so_reward_product_line(reward.reward_product_product_id, price_unit, quantity)
        self._create_so_reward_line(price_unit, reward.reward_quantity * quantity, reward_data)
        return True

    def _process_reward_discount(self, reward_data, quantity):
        reward = reward_data[1].reward_id
        if reward.reward_discount_type == 'amount':
            self._create_so_reward_line(reward.reward_discount_amount, quantity, reward_data)
        if reward.reward_discount_type == 'percentage':
            getattr(self, '_process_reward_percentage_on_' + reward.reward_discount_on)(reward_data, quantity)

    def _process_reward_copuon(self, reward_data, quantity):
        pass

    def _process_reward_percentage_on_cart(self, reward_data, quantity):
        self._create_so_reward_line(self.amount_total * (reward_data[1].reward_id.reward_discount_percentage / 100), quantity, reward_data)

    def _process_reward_percentage_on_specific_product(self, reward_data, quantity):
        reward = reward_data[1].reward_id
        for line in self.order_line:
            if line.product_id.id == reward.reward_discount_on_product_id.id:
                if line.product_uom_qty < quantity:
                    line.with_context(nocoupon=True).write({'product_uom_qty': (reward.reward_quantity * quantity)})
                self._create_so_reward_line(line.price_unit * (reward.reward_discount_percentage) / 100, quantity, reward_data)
                return True
        price_unit = self.env['product.template'].search([('product_variant_ids', '=', reward.reward_discount_on_product_id.id)]).list_price
        self._create_so_reward_product_line(reward.reward_discount_on_product_id, price_unit, quantity)
        self._create_so_reward_line(price_unit * (reward.reward_discount_percentage) / 100, quantity, reward_data)
        return True

    def _process_reward_percentage_on_cheapest_product(self, reward_data, quantity):
        list_of_unit_price = []
        for line in self.order_line:
            list_of_unit_price.append(line.price_unit)
        self._create_so_reward_line((min(list_of_unit_price) * (reward_data[1].reward_discount_percentage) / 100), quantity, reward_data)
        return True

    def _create_so_reward_product_line(self, product, unit_price, quantity):
        order_line_obj = self.env['sale.order.line']
        return order_line_obj.create({'product_id': product.id,
                                      'order_id': self.id,
                                      'price_unit': unit_price,
                                      'product_uom_qty': quantity})

    def _create_so_reward_line(self, amount, quantity, reward_data):
        order_line_obj = self.env['sale.order.line']
        #if so already have reward line for same program
        #update qty if current qty is smaller
        #unlink if the applicable product has been deducted
        #i.e HD 1 from HD 2
        for line_data in self.order_line:
            reward_id = self.env.ref('website_sale_coupon.product_product_reward').id
            if line_data.product_id.id == reward_id and line_data.coupon_program_line_id.id == reward_data[1].id:
                if line_data.product_uom_qty + quantity <= 0:
                    line_data.unlink()
                    return True
                return line_data.with_context(nocoupon=True).write({'product_uom_qty': quantity})
        if reward_data[0] is False:
            #if reward is on amount
            return order_line_obj.with_context(nocoupon=True).create({'product_id': reward_id,
                                                                      'order_id': self.id,
                                                                      'price_unit': -amount,
                                                                      'product_uom_qty': quantity,
                                                                      'coupon_program_line_id': reward_data[1].id})
        return order_line_obj.with_context(nocoupon=True).create({'product_id': reward_id,
                                                                  'order_id': self.id,
                                                                  'price_unit': -amount,
                                                                  'product_uom_qty': quantity,
                                                                  'generated_from_line_id': reward_data[0],
                                                                  'coupon_program_line_id': reward_data[1].id})

    def find_coupon_program(self, so_line, domain=[]):
        res = []
        CouponProgram = self.env['sale.couponprogram']
        if so_line.product_id.id != self.env.ref('website_sale_coupon.product_product_reward').id:
            reward_programs = CouponProgram.search(domain + ['|'] +
                                                            ['&', ('purchase_type', '=', 'product')] + self._make_product_domain(so_line) +
                                                            ['&', ('purchase_type', '=', 'category')] + self._make_product_category_domain(so_line))
            if reward_programs:
                for line in self.order_line:
                    if line.product_id.id == so_line.product_id.id:
                        res.append((line.id, reward_programs))
        if res:
            return res

    def find_coupon_program_for_amount(self, domain=[]):
        res = []
        CouponProgram = self.env['sale.couponprogram']
        reward_programs = CouponProgram.search(domain + [
            '&', ('purchase_type', '=', 'amount'), '|',
            '&', ('reward_tax', '=', 'tax_excluded'), ('minimum_amount', '<=', self.amount_total),
            '&', ('reward_tax', '=', 'tax_included'), ('minimum_amount', '<=', self.amount_untaxed)])
        if reward_programs:
            res.append((False, reward_programs))
            return res

    #To delete reward line if reward product has been deleted
    def delete_reward_line(self):
        reward_id = self.env.ref('website_sale_coupon.product_product_reward')
        for line in self.order_line:
            #if purchase type is category and 2 diffrent applicable products are present on cart
            #then one reward line will be there, with originated from id with 1st category product
            #if any product is deleted then to update the reward qty
            if line.product_id == reward_id and line.coupon_program_line_id.purchase_type == 'category':
                qty = self._compute_reward_quantity([line.id, line.coupon_program_line_id])
                line.with_context(nocoupon=True).write({'product_uom_qty': qty * line.coupon_program_line_id.reward_quantity})
            #If reward product line is deleted then check for applicability and delete the line
            #if reward cover line is deleted then delete the reward line
            if line.product_id == reward_id and line.coupon_program_line_id.reward_type == 'product':
                if not self.check_product_on_cart(line.coupon_program_line_id, line.product_uom_qty):
                    line.with_context(nocoupon=True).unlink()
                    return True

    #To check reward product is on cart or not in given qty
    def check_product_on_cart(self, program, qty):
        for line in self.order_line:
            if line.product_id.id == program.reward_product_product_id.id and line.product_uom_qty >= qty:
                return True
        return False

    #if current amount does not satisfy the applicability of amount rule then delete
    #the reward line of purchase type amount
    def delete_reward_amount_line(self):
        reward_id = self.env.ref('website_sale_coupon.product_product_reward')
        for line in self.order_line:
            if line.product_id.id == reward_id and line.generated_from_line_id.id is False:
                line.with_context(nocoupon=True).unlink()
                return True

    #Check if line is deleted from So then check the applicability of all reward lines,
    #if the reward product line is deleted then make the reward qty 0
    #if reward cover is deleted then delete the reward line
    def check_line_deletion(self, vals):
        new_line = []
        old_line = []
        for line in vals.get('order_line'):
            new_line.append(line[1])
        for line in self.order_line:
            old_line.append(line.id)
        if len(new_line) != len(old_line):
            self.delete_reward_line()

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.apply_immediately_reward()
        return res

    @api.multi
    def write(self, vals):
        print"===== in so write"
        res = super(SaleOrder, self).write(vals)
        self.check_line_deletion(vals)
        #to stop the excecution on click of confirm sale
        if self.state == 'draft':
            programs = self.find_coupon_program_for_amount([('program_type', '=', 'apply_immediately')])
            if programs is None:
                self.delete_reward_amount_line()
                return res
            self._process_rewards(programs)
        return res


class GenerateManualCoupon(models.TransientModel):
    _name = 'sale.manual.coupon'

    nbr_coupons = fields.Integer("Number of coupons")
