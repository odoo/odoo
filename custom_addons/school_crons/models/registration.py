# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
import random as rn
from string import ascii_lowercase, ascii_uppercase


class Registration(models.Model):
    _name = 'school.registration'
    _description = 'Student Registration'
    _rec_name = 'student_id'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=1)
    student_id = fields.Many2one('res.partner', string='Student', domain=[('is_student', '=', 'True')])
    rollno = fields.Char(required=True, readonly=True, default='123')
    batch_id = fields.Many2one('school.batch', string='Batch', store=True)
    course_id = fields.One2many(related='batch_id.course_batch_ids', string='Available Course')
    course_select = fields.Many2one(comodel_name='school.course', domain="[('batch_id', '=', batch_id)]",
                                    string='Select Course')
    admission_date = fields.Date('Admission Date', default=lambda self: date.today(), readonly=True)
    total_seats = fields.Integer('Total Seat', related='course_select.total_seats', required=True)
    remaining_seats = fields.Integer('Available Seat', related='course_select.remaining_seats',
                                     readonly=True, required=True)

    @api.model
    def create(self, vals_list):
        roll_no = self.env['ir.sequence'].next_by_code('school.registration') or 'Roll-No'
        vals_list['rollno'] = roll_no
        return super(Registration, self).create(vals_list)

    def write(self, values):
        """Override default Odoo write function and extend."""
        # Do your custom logic here
        return super(Registration, self).write(values)

    def get_registrations(self):
        # self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Courses',
            'res_model': 'school.course',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def get_batch(self):
        # self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch',
            'res_model': 'school.batch',
            'view_mode': 'tree,form',
            'target': 'current',
        }
    # @api.model_create_multi
    # def create(self, vals_list):
    #     roll_no = self.env['ir.sequence'].next_by_
    #     code('school.registration') or 'Roll-No'
    #     vals_list['rollno'] = roll_no
    #     return super(Registration, self).create(vals_list)

    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         res.append((rec.id, rec.student_id.name + '-' + rec.rollno))
    #     return res

    def _create_multiple(self):
        for i in range(4):
            student_id_list = self.env['res.partner'].search([('is_student', '=', True)]).ids
            batch_id_list = self.env['school.batch'].search([]).ids
            course_select_list = self.env['school.course'].search([]).ids
            vals_list = {'student_id': student_id_list[i], 'batch_id': batch_id_list[i], 'course_select': course_select_list[i]}
            self.create(vals_list)

    def _write_multiple(self):
        records = self.env['school.registration'].search([]).ids
        student_id_list = self.env['res.partner'].search([('is_student', '=', True)]).ids
        batch_id_list = self.env['school.batch'].search([]).ids
        course_select_list = self.env['school.course'].search([]).ids
        update_rec_list = [rn.choice(records) for _ in range(5)]
        update_student_list = [rn.choice(student_id_list) for _ in range(5)]
        update_batch_list = [rn.choice(course_select_list) for _ in range(5)]
        update_course_list = [rn.choice(course_select_list) for _ in range(5)]
        print(update_rec_list)
        for i in range(5):
            vals_list = {'student_id': rn.choice(student_id_list), 'batch_id': rn.choice(batch_id_list), 'course_select': rn.choice(course_select_list)}
            self.env['school.course'].browse(rn.choice(records)).write(vals_list)
            print(vals_list)

    # state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
    #                           ('cancel', 'Cancel')], required=True, default='draft')
    #
    # def button_done(self):
    #     for _ in self:
    #         self.write({
    #             'state': 'done'
    #         })
    #
    # def button_reset(self):
    #     for _ in self:
    #         self.write({
    #             'state': 'draft'
    #         })
    #
    # def button_cancel(self):
    #     for _ in self:
    #         self.write({
    #             'state': 'cancel'
    #         })
