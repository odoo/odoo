# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class Registration(models.Model):
    _name = 'task.registration'
    _description = 'Student Registration'
    _rec_name = 'student_id'

    student_id = fields.Many2one('res.partner', string='Student', domain=[('is_student', '=', 'True')])
    batch_id = fields.Many2one('task.batch', string='Batch', store=True)
    course_id = fields.One2many(related='batch_id.course_batch_id', string='Course')
    total_seats = fields.Integer('Total Seat', related='batch_id.total_seats', store=True)
    remaining_seat = fields.Integer('Remaining Seat', related='batch_id.remaining_seat', store=True)
    no_of_year = fields.Integer('No of year', related='course_id.no_of_year', store=True)
    course_select = fields.Many2one(comodel_name='task.course', domain="[('batch_id', '=', batch_id)]", string='Select Course')
    id_student = fields.Char(string='Student ID',compute="_id_student", store=True)
    current_year = fields.Integer('Current Year', default=lambda self: date.today().year, readonly=True)
    payment = fields.Monetary(currency_field=_rec_name, digits=(3,2))

    @api.depends('student_id', 'batch_id', 'course_select', 'current_year')
    def _id_student(self):
        for i in self:
            id = str(i.current_year)[2:] + i.batch_id.name[:3] + i.course_select.name + i.student_id.name[:3]
            i.id_student = id























'''    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
                              ('cancel', 'Cancel')], required=True, default='draft')

    def button_done(self):
        for _ in self:
            self.write({
                'state': 'done'
            })

    def button_reset(self):
        for _ in self:
            self.write({
                'state': 'draft'
            })

    def button_cancel(self):
        for _ in self:
            self.write({
                'state': 'cancel'
            })'''