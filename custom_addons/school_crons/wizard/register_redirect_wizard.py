# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StudentWizard(models.TransientModel):
    _name = 'school.student'
    _description = 'List of Students'
    _rec_name = 'student_id'

    student_id = fields.Many2one('res.partner', string='Select Student', required=True,
                                 default=lambda self: self.env['res.partner'].browse(self._context.get('active_id')))
    registrations_date = fields.Date(required=True, readonly=True,
                                     default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', required=True, string='University',
                                 default=lambda self: self.env['res.company'].search([]).ids[0])

    def enter_registered_button(self):
        return {
            'name': self.student_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.registration',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('student_id', '=', self.student_id.id)]
        }
