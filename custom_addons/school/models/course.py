# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date


class Courses(models.Model):
    _name = 'task.course'
    _description = 'Course'

    # basic fields
    name = fields.Char(string='Course Name', required=True)
    no_of_year = fields.Integer('No of years', required=True)
    start_year = fields.Integer("Course start Year", required=True)
    end_year = fields.Integer("Course end Year", compute='_end_year', store=True)

    # relational field
    student_ids = fields.One2many('task.registration', 'course_select', string='Student', readonly=True)
    batch_id = fields.Many2one('task.batch', string='Batch', store=True)
    total_seats = fields.Integer('Total Seat',default=1, required=True)
    remaining_seats = fields.Integer(compute='calculate_remaining_seats', store=True)
    # register_id = fields.One2many('task.registration', 'course_select', string='Student', readonly=True)
    # students = fields.Many2one(comodel_name='res.partner', string='Students')
    # _sql_constraints = [
    #     ('name_unique_new',
    #      'UNIQUE(name)',
    #      "The course title must be unique"),
    #
    #     ('no_of_year',
    #      'CHECK(no_of_year <= 0)',
    #      "No of year must be grater than or equal to 1"),
    # ]

    @api.depends('student_ids')
    def calculate_remaining_seats(self):
        for rec in self:
            student_count = len(rec.student_ids.ids)
            self.write({
                'remaining_seats': (student_count * 100) / rec.total_seats,
            })

    @api.model
    @api.constrains('total_seats')
    def _total_seats(self):
        for rec in self:
            if self.total_seats <= 0:
                raise exceptions.UserError('Total seat cannot zero or negative number')

    @api.model
    @api.constrains('no_of_year')
    def _no_of_year(self):
        for rec in self:
            if self.no_of_year <= 0:
                raise exceptions.UserError('Total seat cannot zero or negative number')

    @api.model
    @api.depends('start_year', 'no_of_year')
    def _end_year(self):
        for i in self:
            i.end_year = i.start_year + i.no_of_year

    # @api.constrains('no_of_year','student_ids', 'batch_id')
    # def validate_field(self):
    #     for i in self:
    #         pass
    #         if i.no_of_year <= 0 or i.no_of_year:
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
