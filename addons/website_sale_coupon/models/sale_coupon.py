# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from datetime import datetime
from openerp.exceptions import UserError

import hashlib
import random

from openerp import models, fields, api, _


class SaleApplicability(models.Model):
    _name = 'sale.applicability'
    _description = "Sales Coupon Applicability"

    partner_id = fields.Many2one('res.partner', string="Customer", help="Coupon program will work for selected customer only")
    date_from = fields.Date("Date From", help="Date on which program will get activated", default=fields.date.today())
    date_to = fields.Date("Date To", help="Date after which program will get deactivated", default=fields.date.today() + relativedelta(days=1))
    expiration_use = fields.Integer("Expiration use", default=1, help="Number of Times coupon can be Used")
    purchase_type = fields.Selection([('product', 'Product'), ('category', 'Category'),
                                      ('amount', 'Amount')], string="Type", required=True, default="product",
                                     help="Product - On purchase of selected product, reward will be given\n" +
                                          "Category - On purchase of any product from selected category, reward will be given\n" +
                                          "Amount - On Purchase of entered amount or above than, reward will be given")
    product_id = fields.Many2one('product.product', string="Product", help="On Purchase of selected product, reward will be provided")
    product_category_id = fields.Many2one('product.category', string="Product Categoy", help="On purchase of any product from selected category, reward will be given ")
    product_quantity = fields.Integer("Quantity", default=1, help="Minimum quantity of product which is required to get reward")
    minimum_amount = fields.Float(string="Amount", help="Alteast amount, for that customer have to purchase to get the reward")
    applicability_tax = fields.Selection([('tax_included', 'Tax included'), ('tax_excluded', 'Tax excluded')], default="tax_excluded")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one("res.currency", readonly=True, default=lambda self: self.env.user.company_id.currency_id.id)
    product_uom_name = fields.Char(string="Uom", related='product_id.product_tmpl_id.uom_id.name', store=True, readonly=True)


class SaleReward(models.Model):
    _name = 'sale.reward'
    _description = "Sales Coupon Rewards"

    reward_type = fields.Selection([('product', 'Product'),
                                    ('discount', 'Discount'),
                                    ('coupon', 'Coupon'),
                                    ('free_shipping', 'Free Shipping')], string="Free gift", default="product", required=True,
                                   help="Product - Seleted product will be provided reward\n" +
                                        "Discount - Discount will be provided as reward\n" +
                                        "Coupon - Coupon code will be provided for further use as reward\n" +
                                        "Free Shipping - No shipment charge will be applied")
    reward_product_product_id = fields.Many2one('product.product', string="Product", help="Reward Product")
    reward_quantity = fields.Integer(string="Quantity", default=1, help="Reward product quantity")
    reward_gift_program_id = fields.Many2one('sale.couponprogram', string="Coupon program", domain=[('program_type', '=', 'generated_coupon')])
    reward_discount_type = fields.Selection([('no', 'No'), ('percentage', 'Percentage'),
                                             ('amount', 'Fixed Amount')], string="Apply a discount", default="no",
                                            help="No - No discount will be given\n" +
                                                 "Percentage - Entered percentage discount will be given\n" +
                                                 "Amount - Entered fixed amount discount will be given")
    reward_discount_percentage = fields.Float("Discount", help='The discount in percentage')
    reward_discount_amount = fields.Float("Discount", help='The discount in fixed amount')
    reward_discount_on = fields.Selection([('cart', 'On Cart'), ('cheapest_product', 'On Cheapest Product'),
                                           ('specific_product', 'On Specific Product')], string="Discount On", default="cart",
                                          help="On cart - Discount on whole cart\n" +
                                               "Cheapest product - Discount on cheapest product of the cart\n" +
                                               "Specific product - Discount on seleted specific product")
    reward_discount_on_product_id = fields.Many2one('product.product', string="Product",
                                                    help="Reward discount on specific product will be provided on this seleted product")
    reward_tax = fields.Selection([('tax_included', 'Tax included'),
                                   ('tax_excluded', 'Tax excluded')], string="Tax", default="tax_excluded")
    reward_partial_use = fields.Selection([('yes', 'Yes'), ('no', 'No')], default="no", string="Partial use", help="The reward can be used partially or not")
    reward_currency_id = fields.Many2one("res.currency", readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    reward_product_uom_name = fields.Char(string="Uom", related='reward_product_product_id.product_tmpl_id.uom_id.name', store=True, readonly=True)
    reward_discount_on_product_uom_name = fields.Char(string="Uom", related='reward_discount_on_product_id.product_tmpl_id.uom_id.name', store=True, readonly=True)


class SaleCoupon(models.Model):
    _name = 'sale.coupon'
    _description = "Sales Coupon"

    program_id = fields.Many2one('sale.couponprogram', string="Program")
    coupon_code = fields.Char(string="Coupon Code",
                              default=lambda self: 'SC' + (hashlib.sha1(str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
                              required=True, readonly=True, help="Coupon Code")
    nbr_used = fields.Integer(string="Total used")
    nbr_uses = fields.Integer(string="Number of times coupon can be use")
    used_in_order_id = fields.Many2one('sale.order', string="Sale order")
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
    used_by_partner_id = fields.Many2one('res.partner', string="Customer", related='used_in_order_id.partner_id')
    expiration_date = fields.Date("Expiration date", related='program_id.date_to')
    used_discount_amount = fields.Integer("Used discount amount")


class SaleCouponProgram(models.Model):
    _name = 'sale.couponprogram'
    _description = "Sales Coupon Program"
    _inherits = {'sale.applicability': 'applicability_id', 'sale.reward': 'reward_id'}
    name = fields.Char(help="Program name", required=True)
    program_code = fields.Char(string="Program Code")
    program_type = fields.Selection([('apply_immediately', 'Apply Immediately'), ('public_unique_code',
                                     'Public Unique Code'), ('generated_coupon', 'Generated Coupon')],
                                    string="Program Type", required=True, default="apply_immediately",
                                    help="Apply Immediately - No coupon will be required, if applicability is getting matched, reward will be provided\n" +
                                         "Public unique code - Generated unique will be required to get reward\n" +
                                         "Generated coupon - Coupon code will be required to get reward\n")
    active = fields.Boolean(string="Active", default=True, help="Coupon program is active or inactive")
    program_sequence = fields.Integer(string="Sequence", help="According to sequence, one rule is selected from multiple defined rules to apply")
    coupon_ids = fields.One2many('sale.coupon', 'id', string="Coupon Id")
    applicability_id = fields.Many2one('sale.applicability', string="Applicability Id", ondelete='cascade', required=True)
    reward_id = fields.Many2one('sale.reward', string="Reward", ondelete='cascade', required=True)
    count_sale_order = fields.Integer(compute='_compute_so_count', default=0)
    count_coupons = fields.Integer(compute='_compute_coupon_count', default=0)
    state = fields.Selection([('draft', 'Draft'), ('opened', 'Opened'), ('closed', 'Closed')],
                             help="Draft - Program will be save but can not be used\n" +
                                  "Opened - Program cab be used\n" +
                                  "Closed - Program can not be used", default="draft")
    nbr_uses_public_unique_code = fields.Integer(string="Expiration use", default=1, help="maximum number of times, the program can be used")

    _sql_constraints = [
        ('unique_program_code', 'unique(program_code)', 'The program code must be unique!'),
    ]

    @api.onchange('program_type')
    def _set_partial_use(self):
        self.reward_partial_use = 'no'

    def _check_is_program_valid(self):
        if datetime.strptime(self.date_from, "%Y-%m-%d").date() <= fields.date.today() <= datetime.strptime(self.date_to, "%Y-%m-%d").date():
            return True

    def _compute_program_state(self):
        #close the program when count reach to maximum
        expiration_date = datetime.strptime(self.date_to, "%Y-%m-%d").date()
        if (self.program_type == 'public_unique_code' and fields.date.today() > expiration_date) or \
           (self.program_type == 'apply_immediately' and fields.date.today() > expiration_date) or \
           (self.program_type == 'generated_coupon' and fields.date.today() > expiration_date):
                self.write({'state': 'closed'})
                if self.program_type == 'generated_coupon':
                    coupons_obj = self.env['sale.coupon'].search([('program_id', '=', self.id)])
                    for coupon in coupons_obj:
                        coupon.write({'state': 'expired'})

    # @api.onchange('program_type')
    # def _set_program_code(self):
    #     if self.program_type == 'public_unique_code' and self.program_code is False:
    #         self.program_code = self.env['ir.sequence'].next_by_code('sale.couponprogram')

    @api.one
    def _compute_so_count(self):
        self.count_sale_order = self.env['sale.order'].search_count([('coupon_program_ids', '=', self.id)])
        self._compute_program_state()

    def _compute_coupon_count(self):
        self.count_coupons = self.env['sale.coupon'].search_count([('program_id', '=', self.id)])

    def check_is_program_expired(self):
        expiration_date = datetime.strptime(self.date_to, "%Y-%m-%d").date()
        if (self.program_type == 'public_unique_code' and (fields.date.today() > expiration_date or self.count_sale_order == self.nbr_uses_public_unique_code)) or \
           (self.program_type == 'apply_immediately' and fields.date.today() > expiration_date) or \
           (self.program_type == 'generated_coupon' and fields.date.today() > expiration_date):
                return True

    def get_reward_string(self):
        if self.reward_type == 'product':
            return "Free " + self.reward_type + " - " + self.reward_product_product_id.name
        if self.reward_type == 'discount':
            if self.reward_discount_on == 'cart':
                return "Discount on " + self.reward_discount_on
            if self.reward_discount_on == 'specific_product':
                return "Discount on " + self.reward_discount_on_product_id.name
            if self.reward_discount_on == 'cheapest_product':
                return"Discount on cheapest product"

    @api.multi
    def action_view_order(self, context=None):
        res = self.env['ir.actions.act_window'].for_xml_id('website_sale_coupon', 'action_sale_order_tree_view', context=context)
        res['domain'] = [('coupon_program_ids', '=', self.id)]
        return res

    @api.multi
    def action_view_coupons(self, context=None):
        res = self.env['ir.actions.act_window'].for_xml_id('website_sale_coupon', 'action_coupon_tree', context=context)
        res['domain'] = [('program_id', '=', self.id)]
        return res

    @api.multi
    def open_generate_coupon_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Number of coupons',
            'res_model': 'sale.manual.coupon',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.onchange('reward_type')
    def set_default_value(self):
        self.reward_discount_type = 'no'
        self.reward_discount_on = 'cart'
        self.reward_discount_amount = 0
        self.reward_discount_percentage = 0

    @api.one
    def action_opened(self):
        self.state = 'opened'

    @api.one
    def action_closed(self):
        for coupon in self.env['sale.coupon'].search([('program_id', '=', self.id)]):
            coupon.state = 'expired'
        self.state = 'closed'

    @api.one
    def action_draft(self):
        self.state = 'opened'


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
        coupon_applied_status = sale_order_id.apply_coupon_reward(self.textbox_coupon_code)
        if coupon_applied_status.get('error'):
            raise UserError(_(coupon_applied_status.get('error')))
