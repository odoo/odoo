# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class Com(models.Model):
    _name = 'com.com'
    _description = 'Course'

    name = fields.Char(string='Course Name', required=True)
    no_of_year = fields.Integer('No of years', required=True)
    course_year = fields.Integer("Course Year", store=True)
    no_of_student = fields.Integer('No of student', store=True)
    ser = fields.Text(string='search', compute='_ser', store=True)

    @api.model
    @api.constrains('no_of_year')
    def _no_of_year(self):
        for rec in self:
            if self.no_of_year <= 0:
                raise exceptions.UserError('Total seat cannot zero or negative number')

    @api.depends('no_of_student','no_of_year')
    def _ser(self):
        ri8 = self.env['com.com'].search([('no_of_student', '<', '40')])
        ri9 = self.env['com.com'].search([('no_of_student', '>', '40')])
        self.ser = f'''single record----{ri8.name},
                   multiple record------{[i.name for i in ri9]}
                   multiple record-----{[i.name for i in ri9]}
                   multiple record-----{ri9}
                   multiple record-----{ri9.ids}
                '''
