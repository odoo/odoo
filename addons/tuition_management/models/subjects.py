# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SubjectCategory(models.Model):
    _name = 'subject.category'
    _description = 'Subject Category'
    
    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')


class SubjectMaster(models.Model):
    _name = 'subject.master'
    _description = 'Subject Master'
    
    name = fields.Char(string='Subject Name', required=True)
    category_id = fields.Many2one('subject.category', string='Category', required=True)
    description = fields.Text(string='Description')
    
    _order = 'category_id, name'