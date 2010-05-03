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

from osv import fields, osv
from tools.translate import _

class account_budget_report(osv.osv_memory):

    _name = 'account.budget.report'
    _description = 'Account Budget report for analytic account'
    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        }
    _defaults= {
        'date1': time.strftime('%Y-01-01'),
        'date2': time.strftime('%Y-%m-%d'),
        }

    def check_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'account.budget.post',
             'form': data
            }

        data_model = self.pool.get(datas['model']).browse(cr,uid,context['active_id'])
        if not data_model.dotation_ids:
            raise osv.except_osv(_('Insufficient Data!'),_('No Depreciation or Master Budget Expenses Found on Budget %s!') % data_model.name)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.budget',
            'datas': datas,
            }
account_budget_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

