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
    _inherit = "account.common.report"
    _name = 'account.print.journal'
    _description = 'Account Print Journal'

    _columns = {
        'sort_selection': fields.selection([('date','By Date'),
                                            ('ref','By Reference Number'),],
                                              'Entries Sorted By', required=True),
                }

    _defaults = {
        'sort_selection': 'date',
                }

    def _build_context(self, cr, uid, ids, data, context=None):
        period_obj = self.pool.get('account.period')
        result = super(account_print_journal, self)._build_context(cr, uid, ids, data, context=context)
        if not data['form']['period_from'] or not data['form']['period_to']:
            raise osv.except_osv(_('Error'),_('Select Start period and End period'))
        elif (data['form']['period_from'] > data['form']['period_to']):
            raise osv.except_osv(_('Error'),_('Start period should be smaller then End period'))
        period_date_start = period_obj.read(cr, uid, data['form']['period_from'], ['date_start'])['date_start']
        period_date_stop = period_obj.read(cr, uid, data['form']['period_to'], ['date_stop'])['date_stop']
        cr.execute('SELECT id FROM account_period WHERE date_start >= %s AND date_stop <= %s', (period_date_start, period_date_stop))
        result.update({'periods': map(lambda x: x[0], cr.fetchall())})
        return result

        
    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        obj_jperiod = self.pool.get('account.journal.period')
        period_id = data['form']['periods']
        journal_id = data['form']['journal_ids']
        if type(period_id) ==type([]):
            ids_final = []
            for journal in journal_id:
                for period in period_id:
                    ids_journal_period = obj_jperiod.search(cr,uid, [('journal_id','=',journal),('period_id','=',period)], context=context)
                    if ids_journal_period:
                        ids_final.append(ids_journal_period)
                if not ids_final:
                    raise osv.except_osv(_('No Data Available'), _('No records found for your selection!'))
        data['form'].update(self.read(cr, uid, ids, ['sort_selection'])[0])
        data['form']['query_get'] = query_line
        if data['model'] == 'ir.ui.menu':
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.journal.period.print.wiz', 'datas': data, 'nodestroy':True, }
        else:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.journal.period.print', 'datas': data, 'nodestroy':True, }
        
account_print_journal()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: