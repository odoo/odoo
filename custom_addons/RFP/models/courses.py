# -*- coding: utf-8 -*-

from odoo import models, fields


class Courses(models.Model):
    _name = 'rfp.courses'
    _description = 'Courses'

    name = fields.Char(string='Courses Name', required=True)
    about = fields.Text(string='About', size=200, required=True)
    department_id = fields.Many2one('rfp.department', string='Department')
    subject_ids = fields.Many2many('rfp.subject', 'course_subject_rel', 'course_id', 'subject_id', string='Subject', required=True)
