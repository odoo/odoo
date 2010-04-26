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
from osv import fields,osv
import tools

class available_holidays_report(osv.osv):
    _name = "available.holidays.report"
    _auto = False
    _columns = {
        'date': fields.datetime('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'employee_id': fields.many2one ('hr.employee', 'Employee', readonly=True),
        'holiday_status_id': fields.many2one('hr.holidays.status', 'Leave Type', readonly=True),
        'max_leave': fields.float('Allocated Leaves', readonly=True),
        'taken_leaves': fields.float('Taken Leaves', readonly=True),
        'remaining_leave': fields.float('Remaining Leaves',readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'available_holidays_report')
        cr.execute("""
            create or replace view available_holidays_report as (
                select
                    min(h.id) as id,
                    date_trunc('day',h.create_date) as date,
                    to_char(s.create_date, 'YYYY') as year,
                    to_char(s.create_date, 'MM') as month,
                    h.employee_id as employee_id,
                    h.user_id as user_id,
                    h.state as state,
                    h.holiday_status_id as holiday_status_id,
                    sum(number_of_days) as remaining_leave,
                    (select sum(number_of_days_temp) from hr_holidays
                                                     where type='remove'
                                                     and employee_id=h.employee_id
                                                     and holiday_status_id=h.holiday_status_id
                                                     and state='validate') as taken_leaves,
                    (select sum(number_of_days_temp) from hr_holidays
                                                     where type='add'
                                                     and employee_id=h.employee_id
                                                     and holiday_status_id=h.holiday_status_id
                                                     and state='validate') as max_leave
                from hr_holidays h
                left join hr_holidays_status s on (s.id = h.holiday_status_id)
                where h.state='validate'
                and h.employee_id is not null
                and s.active <> 'f'
                group by h.holiday_status_id, h.employee_id,
                         date_trunc('day',h.create_date),to_char(s.create_date, 'YYYY'),
                         to_char(s.create_date, 'MM'),h.user_id,h.state

            )""")
available_holidays_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
