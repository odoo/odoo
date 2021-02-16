# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class Batch(models.Model):
    _name = 'com.batch'
    _description = 'Batch Data'

    name = fields.Char(string='Batch Name', required=True)
    total_seats = fields.Integer('Total Seat', required=True)
    search = fields.Text(string='search')
    read = fields.Text(string='read')
    domain = fields.Text(string='domain')
    browse = fields.Text(string='browse')
    remaining_seat = fields.Integer(compute='calculate_remaining_seats', store=True)
    course_batch_id = fields.One2many('task.course', 'batch_id', store=True)
    no_of_course = fields.Integer(compute='_calculate_no_of_course', store=True)

    @api.depends('course_batch_id')
    def _calculate_no_of_course(self):
        for i in self:
            self.write({
                'no_of_course': len(i.course_batch_id),
            })

    @api.onchange('course_batch_id')
    def calculate_remaining_seats(self):
        for rec in self:
            student_count = 0
            course_ids = rec.course_batch_id.ids
            for c_id in course_ids:
                student_count += self.env['task.course'].browse(c_id).no_of_student
            self.write({
               'remaining_seat': rec.total_seats - student_count
            })

    @api.model
    @api.constrains('total_seats')
    def _total_seats(self):
        for rec in self:
            if self.total_seats <= 0:
                raise exceptions.UserError('Total seat cannot zero or negative number')

    # @api.model
    # def create(self, values):
    #     ff = values['total_seats']
    #     print(ff)
    #     if ff == 0 or ff <= 0 or ff > 60:
    #         values['total_seats'] = 20
    #     rtn = super(Batch, self).create(values)
    #     # if rtn.total_seats == 0 or rtn.total_seats <= 0 or rtn.total_seats > 60:
    #     #     rtn.total_seats = 20
    #     print(rtn['total_seats'])
    #     return rtn
    #
    # def _write(self, values):
    #     # print(values)
    #     # ff = values['total_seats']
    #     # if values['total_seats'] == 0 or values['total_seats'] <= 0 or values['total_seats'] > 60:
    #     #     values['total_seats'] = 20
    #     rtgt = super(Batch, self).write(values)
    #     return rtgt

    # @api.depends('total_seats', 'name')
    # def _trial(self):
    #     # ser = self.env['com.batch'].search([('total_seats', '=', '20')]).ids
    #     # red = self.env['com.batch'].search([('total_seats', '>', '20'),('total_seats', '<', '50')])
    #     # dom = self.env['com.batch'].search(['&',('total_seats', '>', '20'),('total_seats', '<', '50'),'|',('total_seats', '=', '0')])
    #     # brow = self.env['com.batch'].search([('total_seats', '<=', '20')])
    #     self.write({
    #         'search': 'ser',
    #         'read': 'red',
    #         'domain': 'dom',
    #         'browse': 'brow',
    #     })

