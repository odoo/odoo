# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import fields, models, api

class SaasModuleCategory(models.Model):
    _name = 'saas.module.category'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _rec_name = 'complete_name'
    _order = 'parent_left'
    _description = 'Class for creating Module Categories that one wishes to provide as a service.'

    image = fields.Binary(string='Image')
    name = fields.Char(string="Category Name", required=True)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True)
    parent_id = fields.Many2one('saas.module.category', 'Parent Category', ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('saas.module.category', 'parent_id', 'Child Categories')
    parent_left = fields.Integer('Left Parent', index=1)
    parent_right = fields.Integer('Right Parent', index=1)
    module_category = fields.Many2one(comodel_name="saas.module.category", string="Module Category")
    module_count = fields.Integer(string='Modules', compute='_compute_module_count')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_module_count(self):
        read_group_res = self.env['saas.module'].read_group([('categ_id', 'child_of', self.ids)], ['categ_id'], ['categ_id'])
        group_data = dict((data['categ_id'][0], data['categ_id_count']) for data in read_group_res)
        for categ in self:
            module_count = 0
            for sub_categ_id in categ.search([('id', 'child_of', categ.ids)]).ids:
                module_count += group_data.get(sub_categ_id, 0)
            categ.module_count = module_count

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]