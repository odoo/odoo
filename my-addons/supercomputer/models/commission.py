# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Commission(models.Model):
    _inherit = 'product.category'
    _description = 'Category commission'

    rate = fields.Integer()
    minimum_margin = fields.Integer()
