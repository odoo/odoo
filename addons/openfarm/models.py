# -*- coding: utf-8 -*-

from openerp import models, fields, api


class ProductCategory(models.Model):
    """
    OpenFarm Resource Category
    """
    _name = 'openfarm.product.category'

    name = fields.Char(string='Name',  required=True)
    parent_id = fields.Many2one('openfarm.product.category', string='Parent Category')
    children_ids = fields.One2many('openfarm.product.category', 'parent_id', string='Children Categories')


class ProductTemplate(models.Model):
    """
    OpenFarm Resource
    """
    _inherit = 'product.template'

    of_category_id = fields.Many2one('openfarm.product.category', string='OpenFarm Resource Category')

