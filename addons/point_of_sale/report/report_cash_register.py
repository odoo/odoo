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

class report_cash_register(osv.osv):
    _name = "report.cash.register"
    _description = "Point of Sale Cash Register Analysis"
    _auto = False
    _columns = {
        'date': fields.date('Create Date', readonly=True),
        'year': fields.char('Year', size=4),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'state': fields.selection([('draft', 'Quotation'),('open','Open'),('confirm', 'Confirmed')],'Status'),
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'balance_start': fields.float('Opening Balance'),
        'balance_end_real': fields.float('Closing Balance'),
    }
    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_cash_register')
        cr.execute("""
            create or replace view report_cash_register as (
                select
                    min(s.id) as id,
                    to_date(to_char(s.create_date, 'dd-MM-YYYY'),'dd-MM-YYYY') as date,
                    s.user_id as user_id,
                    s.journal_id as journal_id,
                    s.state as state,
                    s.balance_start as balance_start,
                    s.balance_end_real as balance_end_real,
                    to_char(s.create_date, 'YYYY') as year,
                    to_char(s.create_date, 'MM') as month,
                    to_char(s.create_date, 'YYYY-MM-DD') as day
                from account_bank_statement as s
                group by
                        s.user_id,s.journal_id, s.balance_start, s.balance_end_real,s.state,to_char(s.create_date, 'dd-MM-YYYY'),
                        to_char(s.create_date, 'YYYY'),
                        to_char(s.create_date, 'MM'),
                        to_char(s.create_date, 'YYYY-MM-DD'))""")

report_cash_register()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: