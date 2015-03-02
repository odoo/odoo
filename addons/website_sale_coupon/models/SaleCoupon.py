from openerp import models, fields, api
import random
import hashlib


class SaleApplicability(models.Model):
    _name = 'sale.applicability'
    _description = "Sales Coupon Applicability"

    partner_id = fields.Many2one('res.partner', string="Customer", help="Coupon program will work only for the perticular selected customer")
    date_from = fields.Date("Date From", help="Date on which coupon will get activated")
    date_to = fields.Date("Date To", help="Date after which coupon will get deactivated")
    validity_type = fields.Selection(
        [('day', 'Day(s)'),
         ('week', 'Week(s)'),
         ('month', 'Month(s)'),
         ('year', 'Year(s)'),
         ], string='Validity Duration', required=True, default='day',
        help="Validity Duration can be based on either day, month, week or year.")
    validity_duration = fields.Integer("Validity Duration", help="Validity duration can be set according to validity type")
    expiration_use = fields.Integer("Expiration use", default='1', help="Number of Times coupon can be Used")
    purchase_type = fields.Selection([('poroduct', 'Product'), ('category', 'Category'),
                                      ('amount', 'Amount')], string="Type", required=True)
    product_id = fields.Many2one('product.product', string="Target Product")
    product_category_id = fields.Many2one('product.category', string="Target Categoy")
    product_quantity = fields.Integer("Quantity")
    product_uom_id = fields.Many2one('product.uom', string="UoM of Product")
    minimum_amount = fields.Float(string="Amount", help="Alteast amount, for that customer have to purchase to get the reward")
    tax = fields.Selection([('tax_included', 'Tax included'), ('tax_excluded', 'Tax excluded')])
    company_id = fields.Many2one('res.company', string="Company Id")
    currency_id = fields.Many2one("res.currency", readonly=True)


class SaleReward(models.Model):
    _name = 'sale.reward'
    _description = "Sales Coupon Reward"

    reward_type = fields.Selection([('product', 'Product'),
                                    ('discount', 'Discount'),
                                    ('coupon', 'Coupon')], string="Reward Type", help="Type of reward to give to customer")
    reward_shipping_free = fields.Boolean(string="Free Shipping", default=False, help="Shipment of the order is free or not")
    reward_product_product_id = fields.Many2one('product.product', string="Reward Product")
    reward_quantity = fields.Integer(string="Product Quantity")
    reward_product_uom_id = fields.Many2one('product.uom')
    reward_gift_coupon_id = fields.Many2one('sale.couponprogram', string="Coupon Id")
    reward_discount_type = fields.Selection([('no', 'No'), ('percentage', 'Percentage'),
                                           ('amount', 'Amount')], string="Discount Type")
    reward_discount = fields.Float("Discount", help='The discount in percentage or fixed amount')
    reward_discount_on = fields.Selection([('cart'), ('cheapest_product'), ('specific_product')], string="Discount On")
    reward_discount_on_product_id = fields.Many2one('product.product', string="Product")
    reward_tax = fields.Selection([('tax_included', 'Tax included'),
                                   ('tax_excluded', 'Tax excluded')])
    reward_partial_use = fields.Boolean("The reward can be used partially or not")


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

    program_name = fields.Char(help="Program name")
    program_code = fields.Char(string="Code", help="Unique code to provide the reward")
    program_type = fields.Selection([('apply immediately', 'Apply Immediately'), ('public unique code',
                                     'Public Unique Code'), ('generated coupon', 'Generated Coupon')],
                                    string="Program Type", help="The type of the coupon program")
    is_program_active = fields.Boolean(string="Active", default=True, help="Coupon program is active or inactive")
    program_sequence = fields.Integer(string="Sequence", help="According to sequence, one rule is selected from multiple defined rules to apply")
    # Getting the error here
    coupon_ids = fields.One2many('sale.coupon', 'program_id', string="Coupon Id")
    applicability_id = fields.Many2one('sale.applicability', string="Applicability Id")
    reward_id = fields.Many2one('sale.reward', string="Reward Id")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coupon_id = fields.Many2one('sale.coupon', string="Coupon")
