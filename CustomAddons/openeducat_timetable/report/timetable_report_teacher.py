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
import time

from openerp import models, pooler
from openerp.report import report_sxw


class TimeTableTeacherGenerate(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(TimeTableTeacherGenerate, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'get_object': self.get_object,
            'get_full_name': self.get_full_name,
        })

    def get_full_name(self, data):
        faculty_name = self.pool.get('op.faculty').browse(
            self.cr, self.uid, data['faculty_id'][0])
        return ' '.join([
                         faculty_name.name]
                         )

#    def sort_tt(self, data_list):
#        main_list = []
#        f = []
#        for d in data_list:
#            if d['period'] not in f:
#                f.append(d['period'])
#                main_list.append({
#                    'name': d['period'],
#                    'line': {d['day']: d},
#                    'peropd_time': ' To '.join([d['start_datetime'],
#                                                d['end_datetime']])
#                })
#            else:
#                for m in main_list:
#                    if m['name'] == d['period']:
#                        m['line'][d['day']] = d
#        return main_list

    def get_object(self, data):
        data_list = []
        for timetable_obj in pooler.get_pool(self.cr.dbname).get(
            'op.timetable').browse(
                self.cr, self.uid, data['teacher_time_table_ids']):

            timetable_data = {
                'day':timetable_obj.day, 
                'week': timetable_obj.week,          
                'period': timetable_obj.period_id.name,
                'subject': timetable_obj.subject_id.name,
                'note' : timetable_obj.note,
                'batch': timetable_obj.batch_id.code,
                'classroom' : timetable_obj.classroom_id,
            }
            data_list.append(timetable_data)

        ttdl = sorted(data_list, key=lambda k: k['day'])
        final_list = ttdl
        return final_list


class ReportTimeTableTeacherGenerate(models.AbstractModel):
    _name = 'report.openeducat_timetable.report_timetable_teacher_generate'
    _inherit = 'report.abstract_report'
    _template = 'openeducat_timetable.report_timetable_teacher_generate'
    _wrapped_report_class = TimeTableTeacherGenerate


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
