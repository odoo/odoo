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

class OpExam (models.Model):
    _name = "op.exam"
    _description = 'Egzaminai'
    
    xsemester_id = fields.Many2one('op.xsemester', 'Semestras' , required =True )
    faculty_id = fields.Many2one('op.faculty', 'Destytojas', required=False)
    batch_id = fields.Many2one('op.batch', 'Grupe', required=True)
    subject_id = fields.Many2one('op.subject', 'Dalykas', required=True)
    classroom_id = fields.Many2one('op.classroom', 'Auditorija' , required= False)
    course_id = fields.Many2one('op.course', 'Studijų programa' ,required = False)
    
    active = fields.Boolean('Aktyvus' , default = True)
    archived = fields.Boolean('Archyvuoti', default=False)

    day = fields.Selection(
        [('1', 'Pirmadienis'), ('2', 'Antradienis'),
         ('3', 'Trečiadienis'), ('4', 'Ketvirtadienis'),
         ('5', 'Penktadienis'), ('6', 'Šeštadienis')], 'Diena')
    
    note= fields.Char('Komentaras' , size=128)
    start_datetime = fields.Datetime('Pradžia', required=True)
    end_datetime = fields.Datetime('Pabaiga', required=True)
    
    @api.constrains('start_datetime', 'end_datetime')
    def _check_date_time(self):
        if self.start_datetime > self.end_datetime:
            raise ValidationError('End Time cannot be set before Start Time.')