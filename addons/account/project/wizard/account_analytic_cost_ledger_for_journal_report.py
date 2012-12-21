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

class account_analytic_cost_ledger_journal_report(osv.osv_memory):
    _name = 'account.analytic.cost.ledger.journal.report'
    _description = 'Account Analytic Cost Ledger For Journal Report'

    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        'journal': fields.many2many('account.analytic.journal', 'ledger_journal_rel', 'ledger_id', 'journal_id', 'Journals'),
    }

    _defaults = {
        'date1': lambda *a: time.strftime('%Y-01-01'),
        'date2': lambda *a: time.strftime('%Y-%m-%d')
    }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'account.analytic.account',
             'form': data
                 }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.analytic.account.quantity_cost_ledger',
            'datas': datas,
            }

account_analytic_cost_ledger_journal_report()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
