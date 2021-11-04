# -*- coding: utf-8 -*-

from odoo import models, fields, _, tools, SUPERUSER_ID, api
from odoo.exceptions import ValidationError
import datetime


class CustomerInherit(models.Model):
    _inherit = "res.partner"
    _description = "inherit res.partner"

    #main info
    # fg_customer_code = fields.Char("Customer Code")
    # fg_category = fields.Selection(selection=[
    #         ('category1', 'Category 1'),
    #         ('category2', 'Category 2'),
    #         ('category3', 'Category 3')
    #     ],
    # )
    # fg_branch = fields.Char("Branch")

    x_type_of_business = fields.Char("Type of Business")

    #contact
    x_birthdate = fields.Date("Birthdate")
    x_age = fields.Integer("Age")
    x_gender = fields.Selection(selection=[
            ('Male', 'Male'),
            ('Female', 'Female')
        ],
    )

    #other fields
    # fg_credit_limit = fields.Float('Credit Limit', default=0.0)
    # fg_credit_balance = fields.Float('Credit Balance', default=0.0)
    # fg_discount_limit = fields.Float('Discount Limit', default=0.0)
    # fg_discount_balance = fields.Float('Discount Balance', default=0.0)
    # fg_discount_allowance = fields.Float('Discount/Allowance', default=0.0)
    # fg_price_mode = fields.Selection(selection=[
    #         ('pricemode1', 'Price Mode 1'),
    #         ('pricemode2', 'Price Mode 2')
    #     ],
    # )
    # fg_earned_points = fields.Integer('Earned Points', default=0)
    # fg_member_since = fields.Date("Member Since")
    # fg_valid_thru = fields.Date("Valid Thru")

    currentDate = datetime.date.today()

    @api.constrains('fg_birthdate')
    def _check_value(self):
        if self.fg_birthdate >= self.currentDate:
            raise ValidationError(_('Birthdate should not be greater than current date.'))