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
    validity_duration = fields.Integer("Validity Duration", default=1, help="Validity duration can be set according to validity type")
    expiration_use = fields.Integer("Expiration use", default=1, help="Number of Times coupon can be Used")
    purchase_type = fields.Selection([('product', 'Product'), ('category', 'Category'),
                                      ('amount', 'Amount')], string="Type", required=True, default="product")
    product_id = fields.Many2one('product.product', string="Product")
    product_category_id = fields.Many2one('product.category', string="Product Categoy")
    product_quantity = fields.Integer("Quantity", default=1, help="Minimum quantity of product which is required to get reward")
    minimum_amount = fields.Float(string="Amount", help="Alteast amount, for that customer have to purchase to get the reward")
    applicability_tax = fields.Selection([('tax_included', 'Tax included'), ('tax_excluded', 'Tax excluded')], default="tax_excluded")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one("res.currency", readonly=True, default=lambda self: self.env.user.company_id.currency_id.id)
    product_uom_name = fields.Char(string="Uom", related='product_id.product_tmpl_id.uom_id.name', store=True, readonly=True)

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
                                    ('coupon', 'Coupon'),
                                    ('free_shipping', 'Free Shipping')], string="Free gift", help="Type of reward to give to customer", default="product", required=True)
    reward_shipping_free = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Free Shipping", default="no", help="Shipment of the order is free or not")
    reward_product_product_id = fields.Many2one('product.product', string="Product")
    reward_quantity = fields.Integer(string="Quantity", default=1)
    reward_gift_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    reward_discount_type = fields.Selection([('no', 'No'), ('percentage', 'Percentage'),
                                             ('amount', 'Fixed Amount')], string="Apply a discount", default="no")
    reward_discount_percentage = fields.Float("Discount", help='The discount in percentage')
    reward_discount_amount = fields.Float("Discount", help='The discount in fixed amount')
    reward_discount_on = fields.Selection([('cart', 'On cart'), ('cheapest_product', 'On cheapest product'),
                                           ('specific_product', 'On specific product')], string="Discount On", default="cart")
    reward_discount_on_product_id = fields.Many2one('product.product', string="Product")
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
    expiration_date = fields.Date("Expiration date", compute='_set_expiration_date', default=fields.date.today())

    @api.one
    def _set_expiration_date(self):
        self.expiration_date = self.program_id.applicability_id.get_expiration_date(datetime.strptime(self.create_date, "%Y-%m-%d %H:%M:%S").date())


class SaleCouponProgram(models.Model):
    _name = 'sale.couponprogram'
    _description = "Sales Coupon Program"
    _inherits = {'sale.applicability': 'applicability_id', 'sale.reward': 'reward_id'}
    name = fields.Char(help="Program name", required=True)
    program_code = fields.Char(string="Program Code")
    program_type = fields.Selection([('apply_immediately', 'Apply Immediately'), ('public_unique_code',
                                     'Public Unique Code'), ('generated_coupon', 'Generated Coupon')],
                                    string="Program Type", help="The type of the coupon program", required=True, default="apply_immediately")
    active = fields.Boolean(string="Active", default=True, help="Coupon program is active or inactive")
    program_sequence = fields.Integer(string="Sequence", help="According to sequence, one rule is selected from multiple defined rules to apply")
    coupon_ids = fields.One2many('sale.coupon', 'id', string="Coupon Id")
    applicability_id = fields.Many2one('sale.applicability', string="Applicability Id", ondelete='cascade', required=True)
    reward_id = fields.Many2one('sale.reward', string="Reward", ondelete='cascade', required=True)
    count_sale_order = fields.Integer(compute='_compute_so_count', default=0)
    count_coupons = fields.Integer(compute='_compute_coupon_count', default=0)
    state = fields.Selection([('draft', 'Draft'), ('opened', 'Opened'), ('closed', 'Closed')], help="Shows the program states\nDraft - Program will be save but can not be used\nOpened - Program cab be used\nClosed - Program can not be used", default="draft")
    nbr_uses_public_unique_code = fields.Integer(string="Expiration use", default=1)
    sale_order_id = fields.Many2one('sale.order', "Sale order id")

    _sql_constraints = [
        ('unique_program_code', 'unique(program_code)', 'The program code must be unique!'),
    ]

    def _compute_program_state(self):
        #close the program when count reach to maximum
        if self.program_type == 'public_unique_code':
            if fields.date.today() > datetime.strptime(self.date_to, "%Y-%m-%d").date():
                self.write({'state': 'closed'})
        if self.program_type == 'apply_immediately':
            if fields.date.today() > self.applicability_id.get_expiration_date(datetime.strptime(self.create_date, "%Y-%m-%d %H:%M:%S").date()):
                self.write({'state': 'closed'})
        if self.program_type == 'generated_coupon':
            if fields.date.today() > self.applicability_id.get_expiration_date(datetime.strptime(self.create_date, "%Y-%m-%d %H:%M:%S").date()):
                coupons_obj = self.env['sale.coupon'].search([('program_id', '=', self.id)])
                if coupons_obj:
                    for coupon in coupons_obj:
                        coupon.write({'state': 'expired'})
                self.write({'state': 'closed'})

    def _compute_so_count(self):
        count = 0
        sales_order_line = self.env['sale.order.line'].search([('coupon_program_id', '=', self.id)])
        if sales_order_line:
            for order in sales_order_line:
                count += 1
        self.count_sale_order = count
        self._compute_program_state()

    def _compute_coupon_count(self):
        count = 0
        coupons = self.env['sale.coupon'].search([('program_id', '=', self.id)])
        if coupons:
            for coupon in coupons:
                count += 1
        self.count_coupons = count

    def check_is_program_expired(self, coupon_code):
        expiration_date = self.applicability_id.get_expiration_date(datetime.strptime(self.create_date, "%Y-%m-%d %H:%M:%S").date())
        if self.program_type == 'generated_coupon' or 'apply_immediately':
            if fields.date.today() > expiration_date:
                return True
        if self.program_type == 'public_unique_code':
            if fields.date.today() > datetime.strptime(self.date_to, "%Y-%m-%d").date() or \
               self.count_sale_order == self.nbr_uses_public_unique_code:
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
        res = self.env['ir.actions.act_window'].for_xml_id('website_sale_coupon', 'action_order_line_product_tree', context=context)
        res['domain'] = [('coupon_program_id', '=', self.id)]
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
        coupon_applied_satus = sale_order_id.apply_coupon_reward(self.textbox_coupon_code)
        if coupon_applied_satus.get('error'):
            raise UserError(_(coupon_applied_satus.get('error')))
