# -*- coding: utf-8 -*-
from odoo import models, fields
# 帮助的类别
class HelpClass(models.Model):
    '''帮助类别'''
    _name = 'accountcore.help_class'
    _description = '帮助类别'
    name = fields.Char(string='帮助类别', required=True)
    _sql_constraints = [('accountcore_help_class_name_unique', 'unique(name)',
                         '帮助类别名称重复了!')]
# 帮助
class Helpes(models.Model):
    '''详细帮助'''
    _name = 'accountcore.helps'
    _description = '详细帮助'
    name = fields.Char(string='标题', required=True)
    help_class = fields.Many2one('accountcore.help_class',
                                 string='帮助类别',
                                 required=True)
    content = fields.Html(string='内容')
