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
import datetime



class OpPeriod(models.Model):
    _name = 'op.period'
    _description = 'Period'
    _order = 'hour'


    hour = fields.Selection(
        [(8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'),
         (13, '13'), (14, '14'), (15, '15'), (15, '16'), (17, '17'),
         (18, '18'), (19, '19'),(20, '20') ], 'Valanda', required=True , default= 8)
    minute = fields.Selection(
        [('0', '00'), ('15', '15'), ('30', '30'), ('45', '45'),('50', '50') ], 'Minute',
        required=True, default= '0')
    duration = fields.Float('Trukmė', default=1.5 , required=True)
    name = fields.Char(compute='comp_name', store=True , String= 'Paskaitos laikas ')
    
    @api.depends('hour','minute', 'duration')
    def comp_name(self):
        t_hour= datetime.timedelta(hours = self.hour)
        t_minute = datetime.timedelta(minutes = int(self.minute))
        t_start = t_hour + t_minute
        
        t_end=t_start+ datetime.timedelta(hours = self.duration)
        self.name = str(t_start)[:-3] + ' - ' + str(t_end)[:-3]
    
 


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
