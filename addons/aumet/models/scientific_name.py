# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ScientificName(models.Model):
    _name = 'aumet.scientific_name'
    name = fields.Char(string="Name")
    products = fields.One2many("product.template", "scientific_name")
