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

from openerp.osv import fields, osv

class account_budget_crossvered_report(osv.osv_memory):

    _name = "account.budget.crossvered.report"
    _description = "Account Budget crossvered report"
    _columns = {
        'date_from': fields.date('Start of period', required=True),
        'date_to': fields.date('End of period', required=True),
    }
    _defaults = {
        'date_from': lambda *a: time.strftime('%Y-01-01'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'crossovered.budget',
             'form': data
        }
        datas['form']['report'] = 'analytic-full'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'crossovered.budget.report',
            'datas': datas,
        }

account_budget_crossvered_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
