# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class Registration(models.Model):
    _name = 'task.registration'
    _description = 'Student Registration'
    _rec_name = 'student_id'

    student_id = fields.Many2one('res.partner', string='Student', domain=[('is_student', '=', 'True')])
    rollno = fields.Char(required=True, readonly=True, default='rollno')
    batch_id = fields.Many2one('task.batch', string='Batch', store=True)
    course_id = fields.One2many(related='batch_id.course_batch_ids', string='Available Course')
    course_select = fields.Many2one(comodel_name='task.course', domain="[('batch_id', '=', batch_id)]",
                                    string='Select Course')
    admission_date = fields.Date('Admission Date', default=lambda self: date.today(), readonly=True)
    total_seats = fields.Integer('Total Seat', related='course_select.total_seats', readonly=True, required=True)
    remaining_seats = fields.Integer('Available Seat', related='course_select.remaining_seats', readonly=True, required=True)
    # admission_date = fields.Char('Admission Date', default=lambda self: date.today(), readonly=True)
    # payment = fields.Monetary(currency_field=_rec_name, digits=(3,2))

    @api.model
    def create(self, vals_list):
        roll_no = self.env['ir.sequence'].next_by_code('task.registration') or 'Roll-No'
        print(roll_no)
        vals_list['rollno'] = roll_no
        return super(Registration, self).create(vals_list)

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec.student_id.name + '-' + rec.rollno))
        return res






















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