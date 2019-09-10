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

from openerp.osv import fields, osv

class account_common_journal_report(osv.osv_memory):
    _name = 'account.common.journal.report'
    _description = 'Account Common Journal Report'
    _inherit = "account.common.report"
    _columns = {
        'amount_currency': fields.boolean("With Currency", help="Print Report with the currency column if the currency differs from the company currency."),
    }

    def _build_contexts(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = super(account_common_journal_report, self)._build_contexts(cr, uid, ids, data, context=context)

        if data['form']['filter'] == 'filter_date':
            cr.execute('SELECT period_id FROM account_move_line WHERE date >= %s AND date <= %s', (data['form']['date_from'], data['form']['date_to']))
            result['periods'] = map(lambda x: x[0], cr.fetchall())
        elif data['form']['filter'] == 'filter_period':
            result['periods'] = self.pool.get('account.period').build_ctx_periods(cr, uid, data['form']['period_from'], data['form']['period_to'])
        return result

    def pre_print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data['form'].update(self.read(cr, uid, ids, ['amount_currency'], context=context)[0])
        fy_ids = data['form']['fiscalyear_id'] and [data['form']['fiscalyear_id']] or self.pool.get('account.fiscalyear').search(cr, uid, [('state', '=', 'draft')], context=context)
        period_list = data['form']['periods'] or self.pool.get('account.period').search(cr, uid, [('fiscalyear_id', 'in', fy_ids)], context=context)
        data['form']['active_ids'] = self.pool.get('account.journal.period').search(cr, uid, [('journal_id', 'in', data['form']['journal_ids']), ('period_id', 'in', period_list)], context=context)
        return data


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
