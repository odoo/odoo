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
import datetime
import time 


class OpBatch(models.Model):
    _name = 'op.batch'
    _rec_name = "code"
    _order = 'code'

    code = fields.Char('Kodas', size=12, required=True)
    pavadinimas = fields.Char('Pavadinimas', size=64, required=True)
    start_date = fields.Date(
        'Studijų pradžios metai', required=True, default=time.strftime('%Y-09-01'))
    end_date = fields.Date('Studijų pabaigos metai', required=True , default=time.strftime('%Y-07-01'))
    course_id = fields.Many2one('op.course', 'Studijų programa', required=True)
    students = fields.Integer('Studentų skaičius' , default= '10')
    active = fields.Boolean('Aktyvus', default= True)
    pageidavimai = fields.Text('Pageidavimai')
 #   parent_batch_id = fields.Many2one('op.batch', 'Kursas')
    #timetable_ids = fields.One2many('op.timetable', 'batch_id', 'Paskaitos')
    #exam_ids

    @api.depends('end_date', 'active')
    def check_active(self):
        end_date = self.end_date
        current_date = fields.Date.today()
        if current_date <= end_date :
            self.active= True
        else:
            self.active= False


    @api.one
    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        start_date = fields.Date.from_string(self.start_date)
        end_date = fields.Date.from_string(self.end_date)
        if start_date > end_date:
            raise ValidationError("Pabaigos data negali būti ankstesnė nei pradžios.")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self.env.context.get('get_parent_batch', False):
            lst = []
            lst.append(self.env.context.get('course_id'))
            courses = self.env['op.course'].browse(lst)
            while courses.parent_id:
                lst.append(courses.parent_id.id)
                courses = courses.parent_id
            batches = self.env['op.batch'].search([('course_id', 'in', lst)])
            return batches.name_get()
        return super(OpBatch, self).name_search(
            name, args, operator=operator, limit=limit)
        
        _sql_constraints = [
        ('unique_name_batch_id',
         'unique(batch_code)',
         'Tokia grupė jau yra!'),
        
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
