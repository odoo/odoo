from openerp import models, fields, api
from dateutil.relativedelta import relativedelta
import random
import hashlib


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
    product_uom_id = fields.Many2one('product.uom', string="UoM")
    minimum_amount = fields.Float(string="Amount", help="Alteast amount, for that customer have to purchase to get the reward")
    tax = fields.Selection([('tax_included', 'Tax included'), ('tax_excluded', 'Tax excluded')], default="tax_excluded")
    company_id = fields.Many2one('res.company', string="Company")
    currency_id = fields.Many2one("res.currency", readonly=True, default=lambda self: self.env['res.users'].browse(self._uid).company_id.currency_id.id)

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
    _name = 'sale.coupon.reward'
    _description = "Sales Coupon Rewards"

    reward_type = fields.Selection([('product', 'Product'),
                                    ('discount', 'Discount'),
                                    ('coupon', 'Coupon')], string="Free gift", help="Type of reward to give to customer", default="product")
    reward_shipping_free = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Free Shipping", default="no", help="Shipment of the order is free or not")
    reward_product_product_id = fields.Many2one('product.product', string="Product")
    reward_quantity = fields.Integer(string="Quantity", default=1)
    reward_product_uom_id = fields.Many2one('product.uom', string="UoM")
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
    txt_reward = fields.Char(string="Reward", help="Reward on coupon")


class SaleCouponProgram(models.Model):
    _name = 'sale.couponprogram'
    _description = "Sales Coupon Program"
    _inherits = {'sale.applicability': 'applicability_id', 'sale.coupon.reward': 'reward_id'}
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
    applicability_id = fields.Many2one('sale.applicability', string="Applicability Id", ondelete='cascade')
    reward_id = fields.Many2one('sale.coupon.reward', string="Reward", ondelete='cascade')

    @api.onchange('program_type')
    def generate_public_unique_code(self):
        if self.program_type == 'public_unique_code':
            coupon = self.env['sale.coupon'].create({'program_id': self.id})
            self.program_code = coupon.coupon_code

    def generate_coupon(self):
        pass


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _name = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")
    coupon_program_line_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    @api.multi
    def button_confirm(self):
        res = super(SaleOrderLine, self).button_confirm()
        if self[0].order_id.coupon_program_id:
            coupon = self.env['sale.coupon'].create({'program_id': self[0].order_id.coupon_program_id.id})
            print "------coupon ---", coupon['coupon_code']
        return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    typed_code = fields.Char(string="Coupon", help="Please enter the coupon code")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    @api.one
    def apply_coupon(self):
        order_data = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
        program_obj = self.env['sale.couponprogram']
        coupon_obj = self.env['sale.coupon']
        category_obj = self.env['product.template']
        reward_product_id = self.env['product.product'].search([('name', '=', 'Reward')]).id
        #if SO already have reward
        for data in order_data:
            if data['product_id'][0] == reward_product_id:
                return False
        if self.typed_code:
            #check entered code is program code or coupon code
            program_id = program_obj.search([('program_code', '=', self.typed_code)]) or (coupon_obj.search([('coupon_code', '=', self.typed_code)])).program_id
            if program_id:
                for data in order_data:
                    #check for applicability
                    var_category = category_obj.search([('product_variant_ids', '=', data['product_id'][0])]).categ_id.id
                    result1 = program_id.purchase_type == 'product' and data['product_id'][0] == program_id.product_id.id and data['product_uom_qty'] >= program_id.product_quantity
                    result2 = program_id.purchase_type == 'category' and program_id.product_category_id.id == var_category and data['product_uom_qty'] >= program_id.product_quantity
                    result3 = program_id.purchase_type == 'amount' and self.amount_total >= program_id.minimum_amount
                    if result1 or result2 or result3:
                        self.get_reward(program_id)
                        return True
                    return False
        for data1 in order_data:
            result1 = program_obj.search([('purchase_type', '=', 'product'), ('product_id', '=', data1['product_id'][0]), ('product_quantity', '<=', data1['product_uom_qty'])])
            result2 = program_obj.search([('purchase_type', '=', 'amount'), ('minimum_amount', '<=', self['amount_total'])])
            var_category = self.env['product.template'].search([('product_variant_ids', '=', data1['product_id'][0])])['categ_id']['id']
            result3 = program_obj.search([('purchase_type', '=', 'category'), ('product_category_id', '=', var_category), ('product_quantity', '<=', data1['product_uom_qty'])])
            program_id = result1 or result2 or result3
            if program_id:
                self.get_reward(program_id)
                return True

    def check_customer(self, program_id):
        if program_id.partner_id:
            if self.partner_id.id != program_id.partner_id.id:
                return False
        return True

    def get_reward(self, program_id):
        # to provide the reward
        order_data = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
        order_line_obj = self.env['sale.order.line']
        reward_product_id = self.env['product.product'].search([('name', '=', 'Reward')]).id
        if self.check_customer(program_id):
            if program_id.program_type == 'apply_immediately':
                if program_id.reward_type == 'product':
                    #to get unit price of product
                    for line in self.order_line:
                        if line.product_id == program_id.reward_product_product_id:
                            cost = line['price_unit']
                            exit
                    #cost = self.order_id['program_id.reward_product_product_id']['price_unit']
                    for data2 in order_data:
                        if data2['product_id'][0] == program_id.reward_product_product_id.id and data2['product_uom_qty'] >= program_id.reward_quantity:
                            if program_id.product_id == program_id.reward_product_product_id:
                                if data2['product_uom_qty'] >= program_id.product_quantity + program_id.reward_quantity:
                                    order_line_obj.create({'product_id': reward_product_id, 'order_id': self.id, 'price_unit': -cost, 'product_uom_qty': program_id.reward_quantity})
                                    return True
                            else:
                                # when reward and applicability is different
                                order_line_obj.create({'product_id': reward_product_id, 'order_id': self.id, 'price_unit': -cost, 'product_uom_qty': program_id.reward_quantity})
                                return True
                #if reward type is discount
                if program_id.reward_type == 'discount':
                    if program_id.reward_discount_type == 'no':
                        return True
                    if program_id.reward_discount_type == 'amount':
                            order_line_obj.create({'product_id': reward_product_id, 'order_id': self.id, 'price_unit': -program_id.reward_discount_amount})
                    if program_id.reward_discount_type == 'percentage':
                        if program_id.reward_discount_on == 'cart':
                            order_line_obj.create({'product_id': reward_product_id, 'order_id': self.id, 'price_unit': -(self.amount_total * (program_id.reward_discount_percentage)/100)})
                        if program_id.reward_discount_on == 'cheapest_product':
                            #to get checapest product on cart
                            list_cost = []
                            for min_cost in self.order_line:
                                list_cost.append(min_cost['price_unit'])
                                order_line_obj.create({'product_id': reward_product_id, 'order_id': self.id, 'price_unit': -(min(list_cost) * (program_id.reward_discount_percentage)/100)})
                        if program_id.reward_discount_on == 'specific_product':
                            for line in self.order_line:
                                if line.product_id == program_id.reward_discount_on_product_id:
                                    order_line_obj.create({'product_id': reward_product_id + program_id.reward_discount_on_product_id.name, 'order_id': self.id, 'price_unit': -(line['price_unit'] * program_id.reward_discount_percentage)/100})
                                    return True
                # if reward type is coupon
                if program_id.reward_type == 'coupon':
                    print "------ Reward coupon"
                    self.coupon_program_id = program_id.reward_gift_coupon_id

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.apply_coupon()
        return res

    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self.apply_coupon()
        return res


class GenerateManualCoupon(models.TransientModel):
    _name = 'sale.manual.coupon'

    nbr_coupons = fields.Integer("Number of coupons")
