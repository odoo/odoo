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
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import fields,osv
from openerp import tools

class report_timesheet_task_user(osv.osv):
    _name = "report.timesheet.task.user"
    _auto = False
    _order = "name"

    def get_hrs_timesheet(self, cr, uid, ids, name, args, context):
        result = {}
        for record in self.browse(cr, uid, ids, context):
            last_date = datetime.strptime(record.name, '%Y-%m-%d') + relativedelta(months=1) - relativedelta(days=1)
            obj = self.pool.get('hr_timesheet_sheet.sheet.day')
            sheet_ids = obj.search(cr, uid, [('sheet_id.user_id','=',record.user_id.id),('name','>=',record.name),('name','<=',last_date.strftime('%Y-%m-%d'))])
            data_days = obj.read(cr, uid, sheet_ids, ['name','sheet_id.user_id','total_attendance'])
            total = 0.0
            for day_attendance in data_days:
                total += day_attendance['total_attendance']
            result[record.id] = total
        return result

    _columns = {
        'name': fields.char('Date'),
        'year': fields.char('Year', size=4, required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
        'user_id': fields.many2one('res.users', 'User',readonly=True),
        'timesheet_hrs': fields.function(get_hrs_timesheet, string="Timesheet Hours"),
        'task_hrs' : fields.float('Task Hours'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_timesheet_task_user')
        cr.execute(""" create or replace view report_timesheet_task_user as (
        select
         ((r.id*12)+to_number(months.m_id,'999999'))::integer as id,
               months.name as name,
               r.id as user_id,
               to_char(to_date(months.name, 'YYYY/MM/DD'),'YYYY') as year,
               to_char(to_date(months.name, 'YYYY/MM/DD'),'MM') as month,
               (select sum(hours) from project_task_work where user_id = r.id and date between to_date(months.name, 'YYYY/MM/DD') and (to_date(months.name, 'YYYY/MM/DD') + interval '1 month' -
            interval '1 day') ) as task_hrs
        from res_users r,
                (select to_char(p.date,'YYYY-MM-01') as name,
            to_char(p.date,'YYYYMM') as m_id
                from project_task_work p

            union
                select to_char(h.name,'YYYY-MM-01') as name,
                to_char(h.name,'YYYYMM') as m_id
                from hr_timesheet_sheet_sheet_day h) as months

            group by
                r.id,months.m_id,months.name,
                to_char(to_date(months.name, 'YYYY/MM/DD'),'YYYY') ,
                to_char(to_date(months.name, 'YYYY/MM/DD'),'MM')
              ) """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
