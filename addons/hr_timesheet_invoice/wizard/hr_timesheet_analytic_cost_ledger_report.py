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
import time

from osv import osv, fields

class hr_timesheet_analytic_cost_ledger(osv.osv_memory):
    _name = 'hr.timesheet.analytic.cost.ledger'
    _description = 'hr.timesheet.analytic.cost.ledger'
    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True)
                }
    _defaults = {
         'date1': lambda *a: time.strftime('%Y-01-01'),
         'date2': lambda *a: time.strftime('%Y-%m-%d')
                 }
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {
             'ids': 'active_ids' in context and context['active_ids'] or [],
             'model': 'account.analytic.account',
             'form': self.read(cr, uid, ids, context=context)[0]
                 }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr.timesheet.invoice.account.analytic.account.cost_ledger',
            'datas': datas,
            }

hr_timesheet_analytic_cost_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: