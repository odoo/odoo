# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import datetime
from openerp import models, fields, api
from openerp.exceptions import ValidationError




class OpTimetable(models.Model):
    _name = 'op.timetable'
    _description = 'TimeTables'
#    _rec_name = 'timetable_id'

    xsemester_id = fields.Many2one('op.xsemester', 'Semestras' , required =True )
    faculty_id = fields.Many2one('op.faculty', 'Destytojas', required=False)
    batch_id = fields.Many2one('op.batch', 'Grupe', required=True)
    subject_id = fields.Many2one('op.subject', 'Dalykas', required=True)
    classroom_id = fields.Many2one('op.classroom', 'Auditorija' , required= False)
    period_id = fields.Many2one('op.period', 'Paskaitos laikas', required=True)
    day = fields.Selection(
        [(1, 'Pirmadienis'), (2, 'Antradienis'),
         (3, 'Trečiadienis'), (4, 'Ketvirtadienis'),
         (5, 'Penktadienis'), (6, 'Šeštadienis')], 'Diena')
    week = fields.Selection(
        [('1', 'Pirma'), ('2', 'Antra') , ('0', 'Abi')], 'Savaite' , default='0' , required=True)
    
    note= fields.Char('Komentaras' , size=128)
    
    #### OpenEucat dalis
    
    start_datetime = fields.Datetime(
        'Start Time', required=False,
        default=lambda self: fields.Datetime.now())
    end_datetime = fields.Datetime('End Time', required=False ,default=lambda self: fields.Datetime.now() )
    course_id = fields.Many2one('op.course', 'Course', required=False)
    
    color = fields.Integer('Color Index')
    type = fields.Selection(
        [('Monday', 'Monday'), ('Tuesday', 'Tuesday'),
         ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'),
         ('Friday', 'Friday'), ('Saturday', 'Saturday')], 'Days')
    
    ### functions 
    @api.constrains('start_datetime', 'end_datetime')
    def _check_date_time(self):
        if self.start_datetime > self.end_datetime:
            raise ValidationError(
                'End Time cannot be set before Start Time.')

    @api.onchange('course_id')
    def onchange_course(self):
        self.batch_id = False

    @api.onchange('start_datetime')
    def onchange_start_date(self):
        start_datetime = datetime.datetime.strptime(
            self.start_datetime, "%Y-%m-%d %H:%M:%S")
        if start_datetime and start_datetime.weekday() == 0:
            self.type = 'Monday'
        elif start_datetime and start_datetime.weekday() == 1:
            self.type = 'Tuesday'
        elif start_datetime and start_datetime.weekday() == 2:
            self.type = 'Wednesday'
        elif start_datetime and start_datetime.weekday() == 3:
            self.type = 'Thursday'
        elif start_datetime and start_datetime.weekday() == 4:
            self.type = 'Friday'
        elif start_datetime and start_datetime.weekday() == 5:
            self.type = 'Saturday'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
