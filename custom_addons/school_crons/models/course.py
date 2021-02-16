# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import random as rn
from string import ascii_lowercase, ascii_uppercase


class Courses(models.Model):
    _name = 'school.course'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _description = 'Course'

    # basic fields
    name = fields.Char(string='Course Name', required=True, tracking=True)
    no_of_year = fields.Integer('No of years', required=True)
    start_year = fields.Integer("Course start Year", required=True)
    end_year = fields.Integer("Course end Year", compute='_end_year', store=True)

    # relational field
    student_ids = fields.One2many('school.registration', 'course_select', string='Student')
    batch_id = fields.Many2one('school.batch', string='Batch', store=True)
    total_seats = fields.Integer('Total Seat', default=1, required=True)
    remaining_seats = fields.Integer(compute='calculate_remaining_seats', store=True)

    # Practice
    reg_std_ids = fields.Many2many('res.partner', string='Registered Student', domain=[('is_student', '=', True)])

    def get_registrations(self):
        # self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registrations',
            'view_mode': 'tree',
            'res_model': 'school.registration',
            'target': 'current',
            'domain': [('course_select', '=', self.name)],
        }

    def get_batch(self):
        # self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch',
            'view_mode': 'tree',
            'res_model': 'school.batch',
            'target': 'current',
            'domain': [('course_batch_ids.name', '=', self.name)],
        }

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

    @api.model
    def create(self, vals_list):
        return super(Courses, self).create(vals_list)

    def write(self, values):
        return super(Courses, self).write(values)

    def _create_multiple_course(self):
        for i in range(4):
            name = [''.join(rn.choice(ascii_uppercase) for i in range(1)) + ''.join(rn.choice(ascii_lowercase) for i in range(4))]
            student_id_list = self.env['res.partner'].search([('is_student', '=', True)]).ids
            batch_id_list = self.env['school.batch'].search([]).ids
            course_select_list = self.env['school.course'].search([]).ids
            vals_list = {'name': name, 'no_of_year': 2, 'start_year': 2020,
                         'student_ids': [(0, 0, {'student_id': rn.choice(student_id_list)})],
                         # (0, 0, values)
                         # append new record from many2one field, if we passing list of ids,
                         # all record assign this field that ,present in list,
                         # student_ids = One2many, student_id=Many2one from res.partner
                         # 'student_ids': [(0,0,{'student_id':97})],
                         'batch_id': batch_id_list[i],
                         'reg_std_ids': student_id_list}
            self.create(vals_list)

    def _write_multiple_course(self):
        course_id_list = self.env['school.course'].search([]).ids
        student_id_list = self.env['res.partner'].search([('is_student', '=', True)]).ids
        batch_id_list = self.env['school.batch'].search([]).ids
        for rec in course_id_list:
            name = rn.choice(ascii_uppercase) + ''.join(rn.choice(ascii_lowercase) for i in range(4))
            update_student_list1 = [rn.choice(student_id_list) for _ in range(5)]
            vals_list = {'name': name, 'no_of_year': 3, 'start_year': 2020,
                         'student_ids': [(0,0,{'student_id': rn.choice(student_id_list)})],
                         # ----------------------------------------
                         # reg_std_ids is many2many field
                         # ----------------------------------------
                         # (1, id, values) not used in create method
                         # updates an existing record of id id with the values in values
                         # 'reg_std_ids': [(1, rn.choice(student_id_list), {'name': 'qwerty', 'is_student':True}),
                         #                 (1, rn.choice(student_id_list), {'name': 'qwerty12', 'is_student':True}),
                         #                 (1, rn.choice(student_id_list), {'name': 'qwerty123', 'is_student':True})],
                         # ----------------------------------------
                         # (2, id, 0) Can not be used in create().
                         # removes the record of id id from the set, then deletes it
                         # 'reg_std_ids': [(2, rn.choice(student_id_list), 0),
                         #                 (2, rn.choice(student_id_list), 0),
                         #                 (2, rn.choice(student_id_list), 0)],
                         # ----------------------------------------
                         # (3, id, 0) Can not be used in create().
                         # removes the record of id id from the set, but does not delete it.
                         # 'reg_std_ids': [(3, rn.choice(student_id_list), 0),
                         #                 (3, rn.choice(student_id_list), 0),
                         #                 (3, rn.choice(student_id_list), 0)],
                         # ----------------------------------------
                         # (4, id, 0)
                         # adds an existing record of id id to the set.
                         # ----------------------------------------
                         # 'reg_std_ids': [(4, rn.choice(student_id_list), 0),
                         #                 (4, rn.choice(student_id_list), 0),
                         #                 (4, rn.choice(student_id_list), 0)],
                         # ----------------------------------------
                         # (5, 0, 0)  Can not be used in create().
                         # removes all records from the set,
                         # equivalent to using the command 3 on every record explicitly.
                         # 'reg_std_ids': [(5, 0, 0)],
                         # ----------------------------------------
                         # (6, 0, ids)  Can not be used in create().
                         # replaces all existing records in the set by the ids list,
                         # equivalent to using the command 5 followed by a command 4 for each id in ids.
                         # 'reg_std_ids': [(6, 0, [rn.choice(student_id_list),
                         #                         rn.choice(student_id_list),
                         #                         rn.choice(student_id_list)])],
                         # ----------------------------------------
                         # 5 and 4 combination
                         # replaces all existing records in the set by the ids list,
                         # equivalent to using the command 5 followed by a command 4 for each id in ids.
                         # 'reg_std_ids': [(5, 0, 0), (4, 101, 0), (4, 102, 0)],
                         # ----------------------------------------
                         # (5,0, 0) and (0, 0, values)
                         # clear existing record set and create new data then assign
                         # 'reg_std_ids': [(5, 0, 0),
                         #                 (0, 0, {'name': 'xyz','is_student':True}),
                         #                 (0, 0, {'name': 'xyz12','is_student':True}),
                         #                 (0, 0, {'name': 'xyz1234','is_student':True}),
                         #                 (0, 0, {'name': 'xyz11234','is_student':True}),
                         #                 ],
                         'batch_id': update_student_list1}
            self.env['school.course'].browse(rec).write(vals_list)
            print(vals_list)


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
