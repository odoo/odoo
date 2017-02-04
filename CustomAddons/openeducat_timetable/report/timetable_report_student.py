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

class TimeTableStudentGenerate(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(TimeTableStudentGenerate, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_object': self.get_object
        })

    def sort_tt(self, data_list):
        main_list = []
        for d in data_list:
                main_list.append({
                    'name': d['day'],
                    'line': {d['day']: d}
                })
            
        return main_list
    def get_days(self, data):
        day1=0
        day2=0
        day3=0
        day4=0
        day5=0
        day6=0
        for timetable_obj in pooler.get_pool(self.cr.dbname).get(
            'op.timetable').browse(
                self.cr, self.uid, data['time_table_ids']):
                
            cc = timetable_obj.day
            if cc=='1' :
                day1= day1 +1
            if cc=='2' :
                day2= day1 +1
            if cc=='3' :
                day3= day1 +1
            if cc=='4' :
                day4= day1 +1
            if cc=='5' :
                day5= day1 +1
            if cc=='6' :
                day6= day6 +1

        days_list= [day1,day2,day3,day4,day5,day6]
                    
        print days_list
        return days_list
    def get_object(self, data):


        data_list = []
        for timetable_obj in pooler.get_pool(self.cr.dbname).get(
            'op.timetable').browse(
                self.cr, self.uid, data['time_table_ids']):
            day=timetable_obj.day
            if timetable_obj.note:
                subject= timetable_obj.subject_id.name + ' ' +timetable_obj.note
            else:
                subject=timetable_obj.subject_id.name
            timetable_data = {
                'period': timetable_obj.period_id.name,
                'day': day,
                'hour': timetable_obj.period_id.hour,
                'subject': subject,
                'week': timetable_obj.week,
                'faculty' : timetable_obj.faculty_id.name,
                'classroom': timetable_obj.classroom_id.code
            }
            data_list.append(timetable_data)
                
        ttdl = sorted(data_list, key=lambda k: k['hour'])
        final_list= self.sort_tt(ttdl)
        return final_list
               


class ReportTimetableStudentGenerate(models.AbstractModel):
    _name = 'report.openeducat_timetable.report_timetable_student_generate'
    _inherit = 'report.abstract_report'
    _template = 'openeducat_timetable.report_timetable_student_generate'
    _wrapped_report_class = TimeTableStudentGenerate


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
