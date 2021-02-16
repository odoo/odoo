# -*- coding: utf-8 -*-

from odoo import models, fields


class Subject(models.Model):
    _name = 'rfp.subject'
    _description = 'Subject'

    name = fields.Char(string='Subject Name', required=True)
    course_id = fields.Many2many('rfp.courses', 'courses_subject_rec', string='Subject', required=True)
