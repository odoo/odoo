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

class account_central_journal(osv.osv_memory):
    _name = 'account.central.journal'
    _description = 'Account Central Journal'
    _inherit = "account.common.report"
    _defaults={
               'filter': 'filter_period'
               }

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
            periods = data['form']['periods']
            data['ids'] = ids
            obj_jperiod = self.pool.get('account.journal.period')
            if isinstance(periods, list):
                ids_final = []
                for journal in data['form']['journal_ids']:
                    for period in periods:
                        ids_journal_period = obj_jperiod.search(cr,uid, [('journal_id','=',journal),('period_id','=',period)], context=context)
                        if ids_journal_period:
                            ids_final.append(ids_journal_period)
                if not ids_final:
                    raise osv.except_osv(_('No Data Available'), _('No records found for your selection!'))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.central.journal.wiz',
                'datas': data,
                'nodestroy':True,
                }

account_central_journal()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: