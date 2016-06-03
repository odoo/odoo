# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    target_sales_won = fields.Integer(string='Won in Opportunities Target')
    target_sales_done = fields.Integer(string='Activities Done Target')
