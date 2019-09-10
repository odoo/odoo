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


class account_analytic_journal_report(osv.osv_memory):
    _name = 'account.analytic.journal.report'
    _description = 'Account Analytic Journal'

    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        'analytic_account_journal_id': fields.many2many('account.analytic.journal', 'account_analytic_journal_name', 'journal_line_id', 'journal_print_id', 'Analytic Journals', required=True),
    }

    _defaults = {
        'date1': lambda *a: time.strftime('%Y-01-01'),
        'date2': lambda *a: time.strftime('%Y-%m-%d')
    }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        ids_list = []
        if context.get('active_id',False):
            ids_list.append(context.get('active_id',False))
        else:
            record = self.browse(cr,uid,ids[0],context=context)
            for analytic_record in record.analytic_account_journal_id:
                ids_list.append(analytic_record.id)
        datas = {
            'ids': ids_list,
            'model': 'account.analytic.journal',
            'form': data
        }
        context2 = context.copy()
        context2['active_model'] = 'account.analytic.journal'
        context2['active_ids'] = ids_list
        return self.pool['report'].get_action(cr, uid, [], 'account.report_analyticjournal', data=datas, context=context2)

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(account_analytic_journal_report, self).default_get(cr, uid, fields, context=context)
        if not context.has_key('active_ids'):
            journal_ids = self.pool.get('account.analytic.journal').search(cr, uid, [], context=context)
        else:
            journal_ids = context.get('active_ids')
        if 'analytic_account_journal_id' in fields:
            res.update({'analytic_account_journal_id': journal_ids})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
