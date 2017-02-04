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

from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api
from openerp.exceptions import ValidationError


class TimeTableReport(models.TransientModel):
    _name = 'time.table.report'
    _description = 'Tvarkarascio PDF'

    state = fields.Selection(
        [('faculty', 'Destytojo'), ('student', 'Studento')],
        string='Pasirinkti', required=True, default='student')
    batch_id = fields.Many2one('op.batch', 'Grupe')
    faculty_id = fields.Many2one('op.faculty', 'Destytojas')
    xsemester_id = fields.Many2one('op.xsemester' , 'Semestras', required= True)


    @api.multi
    def gen_time_table_report(self):
        data = self.read(
            [ 'batch_id', 'state',
             'faculty_id' , 'xsemester_id'])[0]
        if data['state'] == 'student':
            time_table_ids = self.env['op.timetable'].search(
                [
                 ('batch_id', '=', data['batch_id'][0]),
                 ('xsemester_id', '=', data['xsemester_id'][0])
                 ],
               # order='start_datetime asc')
                    )
            data.update({'time_table_ids': time_table_ids.ids})
            return self.env['report'].get_action(
                self, 'openeducat_timetable.report_timetable_student_generate',
                data=data)
        else:
            teacher_time_table_ids = self.env['op.timetable'].search(
                [
                 ('faculty_id', '=', data['faculty_id'][0]),
                 ('xsemester_id', '=', data['xsemester_id'][0])
                 ],
               # order='start_datetime asc')
                    )

            data.update({'teacher_time_table_ids': teacher_time_table_ids.ids})
            return self.env['report'].get_action(
                self, 'openeducat_timetable.report_timetable_teacher_generate',
                data=data)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
