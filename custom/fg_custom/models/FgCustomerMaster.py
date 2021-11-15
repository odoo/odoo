# -*- coding: utf-8 -*-

from odoo import models, fields, _, tools, SUPERUSER_ID, api
from odoo.exceptions import ValidationError
import datetime


class CustomerInherit(models.Model):
    _inherit = "res.partner"
    _description = "inherit res.partner"


    x_type_of_business = fields.Char("Type of Business")

    #contact
    x_birthdate = fields.Date("Birthdate")
    x_age = fields.Integer("Age")
    x_gender = fields.Selection(selection=[
            ('Male', 'Male'),
            ('Female', 'Female')
        ],
    )


    currentDate = datetime.date.today()

    @api.constrains('fg_birthdate')
    def _check_value(self):
        if self.fg_birthdate >= self.currentDate:
            raise ValidationError(_('Birthdate should not be greater than current date.'))