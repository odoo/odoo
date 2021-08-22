# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductScientific(models.Model):
    _name = "product.scientific.name"
    
    name = fields.Char(string="Name",required=True)