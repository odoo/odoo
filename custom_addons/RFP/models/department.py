# -*- coding: utf-8 -*-

from odoo import models, fields


class Department(models.Model):
    _name = 'rfp.department'
    _description = 'Department'

    name = fields.Char(string='Department Name', size=20, required=True)
    about = fields.Text(string='About', size=200, required=True)
    cources_ids = fields.One2many('rfp.courses', 'department_id', string='Course')
    faculty_ids = fields.One2many('rfp.faculty', 'department_id', string='Faculty')
    course_subject = fields.Many2many(related='cources_ids.subject_ids', string='Subjects')

