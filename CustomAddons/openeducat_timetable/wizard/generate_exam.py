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
import pytz
import time
from openerp import models, fields, api
from openerp.exceptions import ValidationError



class GenerateExamsTimeTable(models.TransientModel):
    _name = 'generate.exam.table'
    _description = 'Egzaminų sudarymas'
    # _rec_name = 'course_id'

    course_id = fields.Many2one('op.course', 'Course', required=False)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    xsemester_id = fields.Many2one('op.xsemester' , 'Semestras' , required= True)
    time_table_lines = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines')
    time_table_lines_1 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines',
        domain=[('day', '=', '1')])
    time_table_lines_2 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines',
        domain=[('day', '=', '2')])
    time_table_lines_3 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines',
        domain=[('day', '=', '3')])
    time_table_lines_4 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines',
        domain=[('day', '=', '4')])
    time_table_lines_5 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines',
        domain=[('day', '=', '5')])
    time_table_lines_6 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines',
        domain=[('day', '=', '6')])
    start_date = fields.Date(
        'Start Date', required=False, default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date', required=False)

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        start_date = fields.Date.from_string(self.start_date)
        end_date = fields.Date.from_string(self.end_date)
        if start_date > end_date:
            raise ValidationError("End Date cannot be set before Start Date.")

    @api.onchange('course_id')
    def onchange_course(self):
        self.batch_id = False

    @api.one
    def gen_record(self, line,  self_obj):     
        self.env['op.timetable'].create({
            'xsemester_id': line.obj.xsemester_id.id,     #is default formos                       
            'faculty_id': line.faculty_id.id,
            'subject_id': line.subject_id.id,
            'batch_id': self_obj.batch_id.id,               #is default formos
            'period_id': line.period_id.id,
            'classroom_id': line.period_id.id,
            'week': line.week,
            'day': line.day,
                })
        return True
    @api.one
    def act_gen_time_table(self):
        for line in self.time_table_lines:
            self.act_gen_time_table(line)

        return {'type': 'ir.actions.act_window_close'}
        
        
# 
class GenerateExamTimeTableLine(models.TransientModel):
    _name = 'gen.time.table.line'
    _description = 'Generate Exam Time Table Lines'
    _rec_name = 'day'

    gen_time_table = fields.Many2one(
        'generate.time.table', 'Time Table', required=True)
    
    subject_id = fields.Many2one('op.subject', 'Dalykas', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Dėstytojas', required=False)
    batch_id =fields.Many2one('op.batch', 'Grup', required= False)
    xsemester_id = fields.Many2one('op.xsemester', 'Semestras' , required = True)
    classroom_id = fields.Many2one('op.classroom', 'Auditorija' , required = False)
    period_id = fields.Many2one('op.period', 'Paskaitos laikas',  required=True)
    week = fields.Selection(
        [('1' , 'Pirma'), ('2', 'Antra') , ('0' , 'Abi')], 'Savaite' , default='0' , required=True)
    day = fields.Selection([
        ('1', 'Pirmadienis'),
        ('2', 'Antradienis'),
        ('3', 'Trečiadienis'),
        ('4', 'Ketvirtadienis'),
        ('5', 'Penktadienis'),
        ('6', 'Šeštadienis'),
    ], 'Diena', required=True, default ='1')
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
