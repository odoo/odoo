# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CouponRule(models.Model):
    _name = 'coupon.rule'
    _description = "Coupon Rule"

    rule_date_from = fields.Datetime(string="Start Date", help="Coupon program start date")
    rule_date_to = fields.Datetime(string="End Date", help="Coupon program end date")
    rule_partners_domain = fields.Char(string="Based on Customers", help="Coupon program will work for selected customers only")
    rule_products_domain = fields.Char(string="Based on Products", default=[['sale_ok', '=', True]], help="On Purchase of selected product, reward will be given")
    rule_min_quantity = fields.Integer(string="Minimum Quantity", default=1,
        help="Minimum required product quantity to get the reward")
    rule_minimum_amount = fields.Float(default=0.0, help="Minimum required amount to get the reward")
    rule_minimum_amount_tax_inclusion = fields.Selection([
        ('tax_included', 'Tax Included'),
        ('tax_excluded', 'Tax Excluded')], default="tax_excluded")

    @api.constrains('rule_date_to', 'rule_date_from')
    def _check_rule_date_from(self):
        if any(applicability for applicability in self
               if applicability.rule_date_to and applicability.rule_date_from
               and applicability.rule_date_to < applicability.rule_date_from):
            raise ValidationError(_('The start date must be before the end date'))

    @api.constrains('rule_minimum_amount')
    def _check_rule_minimum_amount(self):
        if self.filtered(lambda applicability: applicability.rule_minimum_amount < 0):
            raise ValidationError(_('Minimum purchased amount should be greater than 0'))

    @api.constrains('rule_min_quantity')
    def _check_rule_min_quantity(self):
        if not self.rule_min_quantity > 0:
            raise ValidationError(_('Minimum quantity should be greater than 0'))
