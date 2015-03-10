from openerp import models, fields, api
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
                                      ('amount', 'Amount')], string="Type", required=True)
    product_id = fields.Many2one('product.product', string="Product")
    product_category_id = fields.Many2one('product.category', string="Product Categoy")
    product_quantity = fields.Integer("Quantity", default=1)
    product_uom_id = fields.Many2one('product.uom', string="UoM")
    minimum_amount = fields.Float(string="Amount", help="Alteast amount, for that customer have to purchase to get the reward")
    tax = fields.Selection([('tax_included', 'Tax included'), ('tax_excluded', 'Tax excluded')], default="tax_excluded")
    company_id = fields.Many2one('res.company', string="Company")
    currency_id = fields.Many2one("res.currency", readonly=True)


class SaleReward(models.Model):
    _name = 'sale.coupon.reward'
    _description = "Sales Coupon Rewards"

    reward_type = fields.Selection([('product', 'Product'),
                                    ('discount', 'Discount'),
                                    ('coupon', 'Coupon')], string="Free gift", help="Type of reward to give to customer", default="product")
    reward_shipping_free = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Free Shipping", default="no", help="Shipment of the order is free or not")
    reward_product_product_id = fields.Many2one('product.product', string="Product")
    reward_quantity = fields.Integer(string="Quantity")
    reward_product_uom_id = fields.Many2one('product.uom', string="UoM")
    reward_gift_coupon_id = fields.Many2one('sale.couponprogram', string="Coupon Id")
    reward_discount_type = fields.Selection([('no', 'No'), ('percentage', 'Percentage'),
                                             ('amount', 'Amount')], string="Apply a discount", default="no")
    reward_discount_percentage = fields.Float("Discount", help='The discount in percentage')
    reward_discount_amount = fields.Float("Discount", help='The discount in fixed amount')
    reward_discount_on = fields.Selection([('cart', 'On cart'), ('cheapest_product', 'On cheapest product'),
                                           ('specific_product', 'On specific product')], string="Discount On", default="cart")
    reward_discount_on_product_id = fields.Many2one('product.product', string="Product")
    reward_tax = fields.Selection([('tax_included', 'Tax included'),
                                   ('tax_excluded', 'Tax excluded')], string="Tax")
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

    # @api.onchange('program_type')
    # def generate_coupon_code(self):
    #     if self.program_type == 'generated_coupon':
    #         coupon = self.env['sale.coupon'].create({'program_id': self.id})
    #         print "coupon is :", coupon

    def generate_coupon(self):
        pass


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _name = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")

    @api.multi
    def button_confirm(self):
        res = super(SaleOrderLine, self).button_confirm()
        if self[0]['order_id']['coupon_program_id']:
            print "----", self[0]['order_id']['coupon_program_id']
            coupon = self.env['sale.coupon'].create({'program_id': self[0]['order_id']['coupon_program_id']['id']})
            print "------coupon ---", coupon['coupon_code']
            exit
    # self._generate_coupon()
    #     # list_product = []
    #     # for line in self:
    #     #     print "------------", line['product_uom_qty']
    #     #     list_product = list_product + [(line['product_id'], line['product_uom_qty'])]
    #     # print "-----", list_product
    #     # dict_product = {}
    #     # for k, v in list_product:
    #     #     try:
    #     #         dict_product[k] += v
    #     #     except KeyError:
    #     #         dict_product[k] = v
    #     # print "-----", dict_product
    #     print "---------", self.read_group(fields=["product_id", "product_uom_qty"], groupby=["product_uom_qty"])
        return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    typed_code = fields.Char(string="Coupon", help="Please enter the coupon code")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")

    @api.one
    def apply_coupon(self):
        #print "------------- ", self.typed_code
       # print self.order_line.read_group(fields=["product_id", "product_uom_qty"], groupby=["product_uom_qty"])
        # for line in self.order_line:
        #     print "==========================", line['product_uom_qty']
        # list_product = []
        # for line in self.order_line:
        #     print "------------", line['product_uom_qty']
        #     list_product = list_product + [(line['product_id'], line['product_uom_qty'])]
        # print "-----", list_product
        # dict_product = {}
        # for k, v in list_product:
        #     try:
        #         dict_product[k] += v
        #     except KeyError:
        #         dict_product[k] = v
        # print "-----", dict_product.keys()
        if self.typed_code:
            print "====== typed code", self.typed_code
            program_id = self.env['sale.couponprogram'].search([('program_code', '=', self.typed_code)])
            if program_id:
                print "----", program_id
                order_data = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
                    #if reward is product
                for data in order_data:
                    print "-----", data['product_id'][0], program_id['applicability_id']['product_id']['id'], data['product_uom_qty'], program_id['applicability_id']['product_quantity']
                    if data['product_id'][0] == program_id['applicability_id']['product_id']['id'] and data['product_uom_qty'] >= program_id['applicability_id']['product_quantity']:
                        if program_id['reward_id']['reward_type'] == 'product':
                        # to get unit price of product
                            print"-----", program_id['reward_id']['reward_type']
                            for line in self.order_line:
                                print "----999", line['product_id'], program_id['reward_id']['reward_product_product_id']
                                if line['product_id'] == program_id['reward_id']['reward_product_product_id']:
                                    # self.env['sale.order.line'].create({'name': program_id['reward_id']['reward_product_product_id']['name'], 'order_id': self.id, 'price_unit': -line['price_unit']})
                                    cost = line['price_unit']
                                    print "----cost ", cost
                                    exit
                            for data2 in order_data:
                                print "----@@@@",  data2['product_id'][0], program_id['reward_id']['reward_product_product_id']['id']
                                if data2['product_id'][0] == program_id['reward_id']['reward_product_product_id']['id']:
                                    print "----000", data2['product_uom_qty'], program_id['reward_id']['reward_quantity']
                                    if program_id['applicability_id']['product_id'] == program_id['reward_id']['reward_product_product_id']:
                                        if data2['product_uom_qty'] >= program_id['applicability_id']['product_quantity'] + program_id['reward_id']['reward_quantity']:
                                            self.env['sale.order.line'].create({'name': program_id['reward_id']['reward_product_product_id']['name'], 'order_id': self.id, 'price_unit': -cost, 'product_uom_qty': program_id['reward_id']['reward_quantity']})
                                            exit
                                    else:
                                        if data2['product_uom_qty'] >= program_id['reward_id']['reward_quantity']:
                                            self.env['sale.order.line'].create({'name': program_id['reward_id']['reward_product_product_id']['name'], 'order_id': self.id, 'price_unit': -cost, 'product_uom_qty': program_id['reward_id']['reward_quantity']})
                                            exit
                                exit
                        elif program_id['reward_id']['reward_type'] == 'discount':
                            if program_id['reward_id']['reward_discount_type'] == 'no':
                                pass
                            elif program_id['reward_id']['reward_discount_type'] == 'amount':
                                    self.env['sale.order.line'].create({'name': 'Reward discount amount', 'order_id': self.id, 'price_unit': -program_id['reward_id']['reward_discount_amount']})
                            elif program_id['reward_id']['reward_discount_type'] == 'percentage':
                                if program_id['reward_id']['reward_discount_on'] == 'cart':
                                    self.env['sale.order.line'].create({'name': 'Reward discount on cart', 'order_id': self.id, 'price_unit': -(self.amount_total * (program_id['reward_id']['reward_discount_percentage'])/100)})
                                elif program_id['reward_id']['reward_discount_on'] == 'cheapest_product':
                                    list_cost = []
                                    for min_cost in self.order_line:
                                        list_cost.append(min_cost['price_unit'])
                                        self.env['sale.order.line'].create({'name': 'Reward discount on cheapest product', 'order_id': self.id, 'price_unit': -(min(list_cost) * (program_id['reward_id']['reward_discount_percentage'])/100)})
                                elif program_id['reward_id']['reward_discount_on'] == 'specific_product':
                                    for line in self.order_line:
                                        if line['product_id'] == program_id['reward_id']['reward_discount_on_product_id']:
                                            self.env['sale.order.line'].create({'name': 'discount on ' + program_id['reward_id']['reward_discount_on_product_id']['name'], 'order_id': self.id, 'price_unit': -(line['price_unit'] * program_id['reward_id']['reward_discount_percentage'])/100})
                                            exit
                                        else:
                                            exit
                        #if reward is coupon
                        elif program_id['reward_id']['reward_type'] == 'coupon':
                            #coupon = self.env['sale.coupon'].create({'program_id': program_id['id']})
                            #print "---------", coupon['coupon_code']
                            print "------ Reward coupon"
                            self.coupon_program_id = program_id['id']
                    exit
            else:
                program_id = self.env['sale.coupon'].search([('coupon_code', '=', self.typed_code)])
                if program_id:
                    pass
                else:
                    pass
                # invalid code
        else:
            order_data = self.env['sale.order.line'].read_group([('order_id', '=', self.id)], ['product_id', 'product_uom_qty'], ['product_id', 'product_uom_qty'])
            var_applicability = self.env['sale.applicability']
            for data1 in order_data:
                result = var_applicability.search([('product_id', '=', data1['product_id'][0]), ('product_quantity', '<=', data1['product_uom_qty'])])
                if result:
                    print "----im here"
                    program_id = self.env['sale.couponprogram'].search([('applicability_id', '=', result[0]['id'])])
                    print "=========", program_id['id'], program_id['reward_id']['reward_type']
                    # Apply immediately
                    if program_id['program_type'] == 'apply_immediately':
                        #if reward is product
                        if program_id['reward_id']['reward_type'] == 'product':
                            # to get unit price of product
                            for line in self.order_line:
                                if line['product_id'] == program_id['reward_id']['reward_product_product_id']:
                                        # self.env['sale.order.line'].create({'name': program_id['reward_id']['reward_product_product_id']['name'], 'order_id': self.id, 'price_unit': -line['price_unit']})
                                    cost = line['price_unit']
                                    print "----cost ", cost
                                    exit
                            for data2 in order_data:
                                print "----@@@@",  data2['product_id'][0], program_id['reward_id']['reward_product_product_id']['id']
                                if data2['product_id'][0] == program_id['reward_id']['reward_product_product_id']['id']:
                                    print "----000", data2['product_uom_qty'], program_id['reward_id']['reward_quantity']
                                    if data1['product_id'] == data2['product_id']:
                                        if data2['product_uom_qty'] >= result[0]['product_quantity'] + program_id['reward_id']['reward_quantity']:
                                            self.env['sale.order.line'].create({'name': program_id['reward_id']['reward_product_product_id']['name'], 'order_id': self.id, 'price_unit': -cost, 'product_uom_qty': program_id['reward_id']['reward_quantity']})
                                            exit
                                    else:
                                        if data2['product_uom_qty'] >= program_id['reward_id']['reward_quantity']:
                                            self.env['sale.order.line'].create({'name': program_id['reward_id']['reward_product_product_id']['name'], 'order_id': self.id, 'price_unit': -cost, 'product_uom_qty': program_id['reward_id']['reward_quantity']})
                                            exit
                                exit
                        #if reward is discount
                        elif program_id['reward_id']['reward_type'] == 'discount':
                            if program_id['reward_id']['reward_discount_type'] == 'no':
                                pass
                            elif program_id['reward_id']['reward_discount_type'] == 'amount':
                                    self.env['sale.order.line'].create({'name': 'Reward discount amount', 'order_id': self.id, 'price_unit': -program_id['reward_id']['reward_discount_amount']})
                            elif program_id['reward_id']['reward_discount_type'] == 'percentage':
                                if program_id['reward_id']['reward_discount_on'] == 'cart':
                                    self.env['sale.order.line'].create({'name': 'Reward discount on cart', 'order_id': self.id, 'price_unit': -(self.amount_total * (program_id['reward_id']['reward_discount_percentage'])/100)})
                                elif program_id['reward_id']['reward_discount_on'] == 'cheapest_product':
                                    list_cost = []
                                    for min_cost in self.order_line:
                                        list_cost.append(min_cost['price_unit'])
                                        self.env['sale.order.line'].create({'name': 'Reward discount on cheapest product', 'order_id': self.id, 'price_unit': -(min(list_cost) * (program_id['reward_id']['reward_discount_percentage'])/100)})
                                elif program_id['reward_id']['reward_discount_on'] == 'specific_product':
                                    for line in self.order_line:
                                        if line['product_id'] == program_id['reward_id']['reward_discount_on_product_id']:
                                            self.env['sale.order.line'].create({'name': 'discount on ' + program_id['reward_id']['reward_discount_on_product_id']['name'], 'order_id': self.id, 'price_unit': -(line['price_unit'] * program_id['reward_id']['reward_discount_percentage'])/100})
                                            exit
                                        else:
                                            exit
                        #if reward is coupon
                        elif program_id['reward_id']['reward_type'] == 'coupon':
                            #coupon = self.env['sale.coupon'].create({'program_id': program_id['id']})
                            #print "---------", coupon['coupon_code']
                            print "------ Reward coupon"
                            self.coupon_program_id = program_id['id']
                exit
            else:
                exit


class GenerateManualCoupon(models.TransientModel):
    _name = 'sale.manual.coupon'

    nbr_coupons = fields.Integer("Number of coupons")
