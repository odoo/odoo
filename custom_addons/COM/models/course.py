# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date


class Courses(models.Model):
    _name = 'task.course'
    _description = 'Course'

    name = fields.Char(string='Course Name', required=True)
    no_of_year = fields.Integer('No of years', required=True)
    student_ids = fields.One2many('task.registration', 'student_id', string='Student')
    students = fields.Many2one(string='Students')
    batch_id = fields.Many2one('task.batch', string='Batch')
    course_year = fields.Integer("Course Year", compute='_current_year', store=True)
    no_of_student = fields.Integer('No of student', compute='_calculate_no_of_student', store=True)
    # _sql_constraints = [
    #     ('name_unique_new',
    #      'UNIQUE(name)',
    #      "The course title must be unique"),
    #
    #     ('no_of_year',
    #      'CHECK(no_of_year <= 0)',
    #      "No of year must be grater than or equal to 1"),
    # ]

    @api.model
    @api.constrains('no_of_year')
    def _no_of_year(self):
        for rec in self:
            if self.no_of_year <= 0:
                raise exceptions.UserError('Total seat cannot zero or negative number')

    @api.onchange('student_ids', 'batch_id')
    def _student(self):
        pass


    @api.depends('student_ids')
    def _calculate_no_of_student(self):
        for i in self:
            self.write({
                'no_of_student': len(i.student_ids),
            })

    def _current_year(self):
        self.course_year = date.today().year

    # @api.constrains('no_of_year','student_ids', 'batch_id')
    # def validate_field(self):
    #     for i in self:
    #         pass
    #         if i.no_of_year <= 0 or i.no_of_year:
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             print(i.no_of_year)
    #             raise exceptions.ValidationError('No of year must be grater than or equal to 1')
    #
    #         if len(i.student_ids) <= 0:
    #             return {
    #                 'warning':{
    #                     'title':'Assign Student',
    #                     'description':'To save course, please select least one student'
    #                 }
    #             }
    #         if i.batch_id:
    #             return {
    #                 'warning':{
    #                     'title':'Assign Batch',
    #                     'description':'To save course, please select Batch'
    #                 }
    #             }
