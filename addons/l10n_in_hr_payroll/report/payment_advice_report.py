# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>).
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
from osv import fields, osv

class payment_advice_report(osv.osv):
    _name = "payment.advice.report"
    _description = "Payment Advice Analysis"
    _auto = False
    _columns = {
        'name':fields.char('Name', size=32, readonly=True),
        'date': fields.date('Date', readonly=True,),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'state':fields.selection([
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('cancel', 'Cancelled'),
        ], 'State', select=True, readonly=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
        'nbr': fields.integer('# Payment Lines', readonly=True),
        'number':fields.char('Number', size=16, readonly=True),
        'bysal': fields.float('By Salary', readonly=True),
        'bank_id':fields.many2one('res.bank', 'Bank', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'cheque_nos':fields.char('Cheque Numbers', size=256, readonly=True),
        'neft': fields.boolean('NEFT Transaction', readonly=True),
        'ifsc_code': fields.char('IFSC Code', size=32, readonly=True),
        'employee_bank_no': fields.char('Employee Bank Account', size=32, required=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'payment_advice_report')
        cr.execute("""
            create or replace view payment_advice_report as (
                select
                    min(l.id) as id,
                    sum(l.bysal) as bysal,
                    p.name,
                    p.state,
                    p.date,
                    p.number,
                    p.company_id,
                    p.bank_id,
                    p.chaque_nos as cheque_nos,
                    p.neft,
                    l.employee_id,
                    l.ifsc_code,
                    l.name as employee_bank_no,
                    to_char(p.date, 'YYYY') as year,
                    to_char(p.date, 'MM') as month,
                    to_char(p.date, 'YYYY-MM-DD') as day,
                    1 as nbr
                from
                    hr_payroll_advice as p
                    left join hr_payroll_advice_line as l on (p.id=l.advice_id)
                group by
                    p.number,p.name,p.date,p.state,p.company_id,p.bank_id,p.chaque_nos,p.neft,
                    l.employee_id,l.advice_id,l.bysal,l.ifsc_code, l.name
            )
        """)
payment_advice_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
