# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StudentWizardActionMenu(models.TransientModel):
    _name = 'school.add.student'
    _description = 'Add Students'

    student_ids = fields.Many2many('res.partner', string='Select Student', required=True,)
    course_ids = fields.Many2many('school.course', string='Select Student', required=True,
                                  default=lambda self: self.env['res.partner'].browse(self._context.get('active_ids')))

    def enter_course_button(self):
        for course in self.course_ids:
            course.reg_std_ids += self.student_ids
        return {
            # 'type': 'ir.actions.act_window',
            # 'res_model': 'school.course',
            # 'view_mode': 'tree',
            # 'target': 'current',
            # # 'filter_domain': lambda self: self.env['res.partner'].browse(self._context.get('active_id')).name,
        }