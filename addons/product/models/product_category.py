# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.fields import Domain


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['mail.thread']
    _description = "Product Category"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'parent_id desc, name asc'

    name = fields.Char('Name', index='trigram', required=True, translate=True)
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        search='_search_complete_name',
        recursive=True,
    )
    parent_id = fields.Many2one('product.category', 'Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('product.category', 'parent_id', 'Child Categories')
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products under this category (Does not consider the children categories)")
    product_properties_definition = fields.PropertiesDefinition('Product Properties')

    @api.depends('name', 'parent_id.complete_name')
    @api.depends_context('lang')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _search_complete_name(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return [
            '|',
            ('name', operator, value),
            ('id', 'child_of', self.search([('name', operator, value)]).ids),
        ]

    def _compute_product_count(self):
        read_group_res = self.env['product.template']._read_group([('categ_id', 'child_of', self.ids)], ['categ_id'], ['__count'])
        group_data = {categ.id: count for categ, count in read_group_res}
        for categ in self:
            product_count = 0
            for sub_categ_id in categ.search([('id', 'child_of', categ.ids)]).ids:
                product_count += group_data.get(sub_categ_id, 0)
            categ.product_count = product_count

    @api.model
    def name_create(self, name):
        category = self.create({'name': name})
        return category.id, category.display_name

    @api.depends_context('hierarchical_naming')
    def _compute_display_name(self):
        if self.env.context.get('hierarchical_naming', True):
            return super()._compute_display_name()
        for record in self:
            record.display_name = record.name

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for category, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", category.name)
        return vals_list
