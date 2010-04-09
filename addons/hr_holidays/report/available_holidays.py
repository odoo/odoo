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
class available_holidays_report(osv.osv):
    _name = "available.holidays.report"
        'date': fields.datetime('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'max_leave': fields.float('Allocated Leaves', readonly=True),
        'taken_leaves': fields.float('Taken Leaves', readonly=True),
        'remaining_leave': fields.float('Remaining Leaves',readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        tools.drop_view_if_exists(cr, 'available_holidays_report')
            create or replace view available_holidays_report as (
                    date_trunc('day',h.create_date) as date,
                    to_char(s.create_date, 'YYYY') as year,
                    to_char(s.create_date, 'MM') as month,
                    h.user_id as user_id,
                    h.state as state,
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
                where h.state='validate'
                group by h.holiday_status_id, h.employee_id,
                         date_trunc('day',h.create_date),to_char(s.create_date, 'YYYY'),
                         to_char(s.create_date, 'MM'),h.user_id,h.state

available_holidays_report()
