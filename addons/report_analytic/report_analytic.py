# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class report_analytic_account_close(osv.osv):
    _name = "report.analytic.account.close"
    _description = "Analytic account to close"
    _auto = False
    _columns = {
        'name': fields.many2one('account.analytic.account', 'Analytic account', readonly=True),
        'state': fields.char('State', size=32, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'quantity': fields.float('Quantity', readonly=True),
        'quantity_max': fields.float('Max. Quantity', readonly=True),
        'balance': fields.float('Balance', readonly=True),
        'date_deadline': fields.date('Deadline', readonly=True),
    }
    def init(self, cr):
        cr.execute("""
            create or replace view report_analytic_account_close as (
                select
                    a.id as id,
                    a.id as name,
                    a.state as state,
                    sum(l.unit_amount) as quantity,
                    sum(l.amount) as balance,
                    a.partner_id as partner_id,
                    a.quantity_max as quantity_max,
                    a.date as date_deadline
                from
                    account_analytic_line l
                right join
                    account_analytic_account a on (l.account_id=a.id)
                group by
                    a.id,a.state, a.quantity_max,a.date,a.partner_id
                having
                    (a.quantity_max>0 and (sum(l.unit_amount)>=a.quantity_max)) or
                    a.date <= current_date
            )""")
report_analytic_account_close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

