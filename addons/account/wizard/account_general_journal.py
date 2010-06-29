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

class account_general_journal(osv.osv_memory):
    _inherit = "account.common.report"
    _name = 'account.general.journal'
    _description = 'Account General Journal'

    def _build_context(self, cr, uid, ids, data, context=None):
        result = super(account_general_journal, self)._build_context(cr, uid, ids, data, context=context)
        if data['form']['filter'] == 'filter_date':
            cr.execute('SELECT period_id FROM account_move_line WHERE date >= %s AND date <= %s', (data['form']['date_from'], data['form']['date_to']))
            result['periods'] = map(lambda x: x[0], cr.fetchall())
        return result


    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        data['form'].update(self.read(cr, uid, ids, ['sort_selection'])[0])
        fy_ids = data['form']['fiscalyear_id'] and [data['form']['fiscalyear_id']] or self.pool.get('account.fiscalyear').search(cr, uid, [('state', '=', 'draft')], context=context)
        period_list = data['form']['periods'] or self.pool.get('account.period').search(cr, uid, [('fiscalyear_id', 'in', fy_ids)], context=context)
        data['form']['active_ids'] = self.pool.get('account.journal.period').search(cr, uid, [('journal_id', 'in', data['form']['journal_ids']), ('period_id', 'in', period_list)], context=context)
        data['form']['query_get'] = query_line
        return {'type': 'ir.actions.report.xml', 'report_name': 'account.general.journal', 'datas': data, 'nodestroy':True, }

account_general_journal()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
