# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class Batch(models.Model):
    _name = 'school.batch'
    _description = 'Batch Data'

    name = fields.Char(string='Batch Name', required=True)
    course_batch_ids = fields.One2many('school.course', 'batch_id', store=True)
    no_of_course = fields.Integer(compute='_calculate_no_of_course', store=True)

    @api.depends('course_batch_ids')
    def _calculate_no_of_course(self):
        for i in self:
            self.write({
                'no_of_course': len(i.course_batch_ids),
            })
