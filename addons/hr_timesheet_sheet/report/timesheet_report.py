# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import tools
from osv import fields,osv

class timesheet_report(osv.osv):
    _name = "timesheet.report"
    _description = "Timesheet by month "
    _auto = False
    _columns = {
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'no_of_timesheet': fields.integer('Total Timesheet',readonly=True),
        'total_att': fields.float('Total Attendance'),
        'total_ts': fields.float('Total Timesheet'),
        'year': fields.char('Remaining leaves', size=4),
        'name': fields.char('Name', size=64),
        'user_id': fields.many2one('res.users','User'),
        'leave_type': fields.char('Leave Type',size=64),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'timesheet_report')
        cr.execute("""
            create or replace view timesheet_report as (
                    SELECT sheet.name as name, 
                           min(sheet.id) as id,
                           to_char(sheet.date_current, 'YYYY') as year,
                           to_char(sheet.date_current, 'MM') as month,
                           sum(day.total_attendance) as total_att,
                           sum(day.total_timesheet) as total_ts,
                           sheet.user_id as user_id
                    FROM hr_timesheet_sheet_sheet AS sheet
                    LEFT JOIN hr_timesheet_sheet_sheet_day AS day
                    ON (sheet.id = day.sheet_id)
                    GROUP BY sheet.name, year, month, user_id
                    ) """)

timesheet_report()
