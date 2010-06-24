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
import tools

class account_common_report(osv.osv_memory):
    _name = "account.common.report"
    _description = "Common Report"

    _columns = {
        'chart_account_id': fields.many2one('account.account', 'Chart of account', required=True, domain = [('parent_id','=',False)]),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal year', help='Keep empty for all open fiscal year'),

        'filter': fields.selection([('filter_no','No filters'), ('filter_date','Date'), ('filter_period','Periods')],"Filter by:", required=True),

        'period_from': fields.many2one('account.period', 'Start period'),
        'period_to': fields.many2one('account.period', 'End period'),
        #not used. Do we really need it? 'period_ids': fields.many2many('account.period', 'ledger_period_rel', 'ledger_id', 'period_id', 'Periods'),

        'journal_ids': fields.many2many('account.journal', 'account_common_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),

        'date_from': fields.date("Start date"),
        'date_to': fields.date("End date"),

        #'display_account': fields.selection([('bal_mouvement','With movements'), ('bal_all','All'), ('bal_solde','With balance is not equal to 0')],"Display accounts"),
        #'landscape': fields.boolean("Landscape Mode"),
        #'soldeinit': fields.boolean("Include initial balances"),
        #'amount_currency': fields.boolean("With Currency"),

        #'filter': fields.boolean("Landscape Mode"),
        #'state': fields.selection([('bydate','By Date'), ('byperiod','By Period'), ('all','By Date and Period'), ('none','No Filter')],"Date/Period Filter"),
        #'company_id': fields.many2one('res.company', 'Company', required=True),
    }

#    def _get_company(self, cr, uid, context=None):
#        user_obj = self.pool.get('res.users')
#        company_obj = self.pool.get('res.company')
#        if context is None:
#            context = {}
#        user = user_obj.browse(cr, uid, uid, context=context)
#        if user.company_id:
#           return user.company_id.id
#        else:
#           return company_obj.search(cr, uid, [('parent_id', '=', False)])[0]

    def _get_account(self, cr, uid, context=None):
        tmp = self.pool.get('account.account').search(cr, uid, [], limit=1 )
        if not tmp:
            return False
        return tmp[0]

    def _get_fiscalyear(self, cr, uid, context=None):
        now = time.strftime('%Y-%m-%d')
        tmp = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<', now), ('date_stop', '>', now)], limit=1 )
        if not tmp:
            return False
        return tmp[0]

    def _get_all_journal(self, cr, uid, context=None):
        return self.pool.get('account.journal').search(cr, uid ,[])

    _defaults = {
#            'state' : 'none',
            'date_from' : time.strftime('%Y-01-01'),
            'date_to' : time.strftime('%Y-%m-%d'),
#            'company_id' : _get_company,
#            'display_account' : 'bal_all',
#            'sortbydate' : 'sort_date',
            'fiscalyear_id' : _get_fiscalyear,
#            'landscape': True,
#            'amount_currency' : True,
            'journal_ids': _get_all_journal,
            'filter': 'filter_no',
            'chart_account_id': _get_account,
    }

    def _build_context(self, cr, uid, ids, data, context = None):
        result = {}
        result['fiscalyear'] = data['form']['fiscalyear_id'] and data['form']['fiscalyear_id'] or False
        if data['form']['filter'] == 'filter_date':
            result['date_from'] = data['form']['date_from']
            result['date_to'] = data['form']['date_to']
        elif data['form']['filter'] == 'filter_period':
            period_obj = self.pool.get('account.period')
            period_date_start = period_obj.read(cr, uid, data['form']['period_from'], ['date_start'])['date_start']
            period_date_stop = period_obj.read(cr, uid, data['form']['period_to'], ['date_stop'])['date_stop']
            cr.execute('SELECT id FROM account_period WHERE date_start >= %s AND date_stop <= %s', (period_date_start, period_date_stop))
            result['periods'] = lambda x: x[0], cr.fetchall()
        return result

    def _print_report(self, cr, uid, ids, data, query_line, context):
        raise (_('Error'), _('not implemented'))

    def check_report(self, cr, uid, ids, context=None):
        obj_acc_move_line = self.pool.get('account.move.line')
        data = {}
        data['ids'] = context.get('active_ids',[])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id'])[0]
        used_context = self._build_context(cr, uid, ids, data, context)
        query_line = obj_acc_move_line._query_get(cr, uid, obj='l', context=used_context)
        return self._print_report(cr, uid, ids, data, query_line, context)
account_common_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

