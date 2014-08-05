# -*- coding: utf-8 -*-
from openerp import fields, models

class Course(models.Model):
    _name = 'openacademy.course'

    name = fields.Char(string="Title", required=True)
    description = fields.Text()

class Session(models.Model):
    _name = 'openacademy.session'

    name = fields.Char(string="Name", required=True)
    start_date = fields.Date()
    duration = fields.Float(digits=(6, 2), help="Duration in days")
    seats = fields.Integer(string="Number of seats")

class Attendee(models.Model):
    _name = 'openacademy.attendee'

    name = fields.Char()
