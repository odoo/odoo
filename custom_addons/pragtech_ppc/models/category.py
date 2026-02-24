# -*- coding: utf-8 -*-

from odoo import fields, models


class TaskCategories(models.Model):
    _name = 'task.category'
    _description = 'Task Category'

    name = fields.Char('Name', required=True)
    description = fields.Text('Remark/Description')
    sub_category_ids = fields.One2many('task.sub.category', 'category_id')


class TaskSubCategory(models.Model):
    _name = 'task.sub.category'
    _description = 'Task Sub Category'

    name = fields.Char('Name', required=True)
    category_id = fields.Many2one('task.category', 'Category', required=True)
    description = fields.Text('Remark/Description')


class LabourCategory(models.Model):
    _name = 'labour.category'
    _description = 'Labour Category'

    name = fields.Char('Name', required=True)
    description = fields.Text('Remark/Description')
    sub_category_ids = fields.One2many('labour.sub.category', 'category_id')


class LabourSubCategory(models.Model):
    _name = 'labour.sub.category'
    _description = 'Labour Sub Category'

    name = fields.Char('Name', required=True)
    category_id = fields.Many2one('labour.category', 'Labour Category')
    description = fields.Text('Remark/Description')

