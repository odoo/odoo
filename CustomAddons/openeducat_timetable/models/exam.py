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

from openerp import models, fields, api
from openerp.exceptions import ValidationError
import datetime, time

class OpExam (models.Model):
    _name = "op.exam"
    _description = 'Egzaminai'
    _order = 'start_date'
    #_rec_name= 'id'
    xsemester_id = fields.Many2one('op.xsemester', 'Semestras' , required =True, defult=1 )
    faculty_id = fields.Many2one('op.faculty', 'Destytojas', required=True)
    batch_id = fields.Many2one('op.batch', 'Grupe', required=True)
    subject_id = fields.Many2one('op.subject', 'Dalykas', required=True)
    classroom_id = fields.Many2one('op.classroom', 'Auditorija' , required= False)
    notes= fields.Char("Komentaras" , size= 64, require= False)
    
    active = fields.Boolean('Aktyvus' , default = True)
    color = fields.Integer('Color Index')
    day = fields.Selection(
        [('1', 'Pirmadienis'), ('2', 'Antradienis'),
         ('3', 'Trečiadienis'), ('4', 'Ketvirtadienis'),
         ('5', 'Penktadienis'), ('6', 'Šeštadienis')], 'Diena')
    semester_start_date = fields.Date('Pradžia', related='xsemester_id.exam_start_date')
    semester_end_date = fields.Date('Pabaiga', related='xsemester_id.exam_end_date')
    exam_timestartint = fields.Integer(compute='comp_time', store=True , String= 'Egzamino laikas ')
    start_date = fields.Date('Egzamino data', required=True  )
    hour = fields.Selection(
        [(8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'),
         (13, '13'), (14, '14'), (15, '15'), (15, '16'), (17, '17'),
         (18, '18'), (19, '19'),(20, '20') ], 'Valanda', required=True , default= 8)
    minute = fields.Selection(
        [('0', '00'), ('15', '15'), ('30', '30'), ('45', '45')], 'Minutė',
        required=True, default= '0')
    duration = fields.Selection(
        [(30, '0:30'), (45, '0:45'), (60, '1:00'), (90, '1:30') , (120,'2:00') , (150,'2:30'), (180, '3:00')], 'Trukmė',
        required=True, default= 90)
    
    exam_time_name = fields.Char(compute='comp_name', store=True , String= 'Egzamino laikas ')
    

    @api.constrains('start_date', 'semester_start_date')
    def _check_date_time(self):
        if self.start_date < self.semester_start_date:
            raise ValidationError('Egzaminas negali būti priskirtas  ankstesnei datai nei prasideda sesija')
        if self.start_date > self.semester_end_date:
            raise ValidationError('Egzaminas negali būti priskirtas  vėlesnei datai nei sesijos pabaiga')
    @api.constrains('start_date','hour', 'minute', 'duration')
    def comp_name(self):
        t_hour= datetime.timedelta(hours = self.hour)
        t_minute = datetime.timedelta(minutes = int(self.minute))
        t_start= t_hour + t_minute
        t_end=t_start+ datetime.timedelta(minutes = self.duration)
        self.exam_time_name  = str(t_start)[:-3] + ' - ' + str(t_end)[:-3]
        
    @api.constrains('hour', 'minute')
    def comp_time(self):
        exam_timestart  =  int(self.hour)*60 + int(self.minute) 
        self.exam_timestartint = int(exam_timestart)

        
#    @api.constrains('start_date','hour', 'minute', 'duration')   
#    def comp_exam_time(self):
#        t_hour= datetime.timedelta(hours = self.hour)
#        t_minute = datetime.timedelta(minutes = int(self.minute))
#        t_duration = datetime.timedelta(minutes = self.duration)
#        t_start = t_hour + t_minute
#        self.exam_time = self.exam_time + t_start + t_duration
    
    