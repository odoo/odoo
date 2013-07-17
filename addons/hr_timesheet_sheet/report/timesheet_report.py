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

from openerp import tools
from openerp.osv import fields,osv

class timesheet_report(osv.osv):
    _name = "timesheet.report"
    _description = "Timesheet"
    _auto = False
    _columns = {
        'year': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'date': fields.date('Date', readonly=True),
        'name': fields.char('Description', size=64,readonly=True),
        'product_id' : fields.many2one('product.product', 'Product'),
        'general_account_id' : fields.many2one('account.account', 'General Account', readonly=True),
        'user_id': fields.many2one('res.users', 'User',readonly=True),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Type of Invoicing',readonly=True),
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account',readonly=True),
        'nbr': fields.integer('#Nbr',readonly=True),
        'total_diff': fields.float('#Total Diff',readonly=True),
        'total_timesheet': fields.float('#Total Timesheet',readonly=True),
        'total_attendance': fields.float('#Total Attendance',readonly=True),
        'company_id': fields.many2one('res.company', 'Company',readonly=True),
        'department_id':fields.many2one('hr.department','Department',readonly=True),
        'date_from': fields.date('Date from',readonly=True,),
        'date_to': fields.date('Date to',readonly=True),
        'date_current': fields.date('Current date', required=True),
        'state' : fields.selection([
            ('new', 'New'),
            ('draft','Draft'),
            ('confirm','Confirmed'),
            ('done','Done')], 'Status', readonly=True),
        'quantity': fields.float('Time',readonly=True),
        'cost': fields.float('#Cost',readonly=True),
        }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'timesheet_report')
        cr.execute("""
            create or replace view timesheet_report as (
                    select
                        min(aal.id) as id,
                        htss.name,
                        aal.date as date,
                        htss.date_from,
                        htss.date_to,
                        to_char(htss.date_from, 'YYYY-MM-DD') as day,
                        to_char(htss.date_from, 'YYYY') as year,
                        to_char(htss.date_from, 'MM') as month,
                        count(*) as nbr,
                        aal.unit_amount as quantity,
                        aal.amount as cost,
                        aal.account_id,
                        aal.product_id,
                        (SELECT   sum(day.total_difference)
                            FROM hr_timesheet_sheet_sheet AS sheet 
                            LEFT JOIN hr_timesheet_sheet_sheet_day AS day 
                            ON (sheet.id = day.sheet_id) where sheet.id=htss.id) as total_diff,
                        (SELECT sum(day.total_timesheet)
                            FROM hr_timesheet_sheet_sheet AS sheet 
                            LEFT JOIN hr_timesheet_sheet_sheet_day AS day 
                            ON (sheet.id = day.sheet_id) where sheet.id=htss.id) as total_timesheet,
                        (SELECT sum(day.total_attendance)
                            FROM hr_timesheet_sheet_sheet AS sheet 
                            LEFT JOIN hr_timesheet_sheet_sheet_day AS day 
                            ON (sheet.id = day.sheet_id) where sheet.id=htss.id) as total_attendance,
                        aal.to_invoice,
                        aal.general_account_id,
                        htss.user_id,
                        htss.company_id,
                        htss.department_id,
                        htss.state
                    from account_analytic_line as aal
                    left join hr_analytic_timesheet as hat ON (hat.line_id=aal.id)
                    left join hr_timesheet_sheet_sheet as htss ON (hat.line_id=htss.id)
                    group by
                        aal.account_id,
                        aal.date,
                        htss.date_from,
                        htss.date_to,
                        aal.unit_amount,
                        aal.amount,
                        aal.to_invoice,
                        aal.product_id,
                        aal.general_account_id,
                        htss.name,
                        htss.company_id,
                        htss.state,
                        htss.id,
                        htss.department_id,
                        htss.user_id
            )
        """)
timesheet_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
