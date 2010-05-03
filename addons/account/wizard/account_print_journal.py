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
from osv import osv, fields
from tools.translate import _

class account_print_journal(osv.osv_memory):
    _name = 'account.print.journal'
    _description = 'Account Print Journal'

    _columns = {
        'journal_id': fields.many2many('account.journal', 'account_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
        'period_id': fields.many2many('account.period', 'account_period_rel', 'account_id', 'period_id', 'Periods',  required=True),
        'sort_selection': fields.selection([('date','By date'),
                                            ('ref','Reference Number'),],
                                              'Entries Sorted By', required=True),
        }

    _defaults = {
        'sort_selection': lambda *a: 'date',
                }

    def check_data(self, cr, uid, ids, context=None):
        obj_jperiod = self.pool.get('account.journal.period')
        datas = {}
        datas['ids'] = []
        datas['model'] = 'account.journal.period'
        datas['form'] = self.read(cr, uid, ids)[0]
        period_id = datas['form']['period_id']
        journal_id = datas['form']['journal_id']

        if type(period_id)==type([]):
            ids_final = []
            for journal in journal_id:
                for period in period_id:
                    ids_journal_period = obj_jperiod.search(cr,uid, [('journal_id','=',journal),('period_id','=',period)], context=context)
                    if ids_journal_period:
                        ids_final.append(ids_journal_period)
                if not ids_final:
                    raise osv.except_osv(_('No Data Available'), _('No records found for your selection!'))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.journal.period.print',
            'datas': datas,
            'nodestroy':True,
            }

account_print_journal()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: