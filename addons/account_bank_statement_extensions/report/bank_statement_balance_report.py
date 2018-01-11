# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
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
from openerp.osv import osv
from openerp.report import report_sxw


class bank_statement_balance_report(report_sxw.rml_parse):

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr

        cr.execute('SELECT s.name as s_name, s.date AS s_date, j.code as j_code, s.balance_end_real as s_balance ' \
                        'FROM account_bank_statement s ' \
                        'INNER JOIN account_journal j on s.journal_id = j.id ' \
                        'INNER JOIN ' \
                            '(SELECT journal_id, max(date) as max_date FROM account_bank_statement ' \
                                'GROUP BY journal_id) d ' \
                                'ON (s.journal_id = d.journal_id AND s.date = d.max_date) ' \
                        'ORDER BY j.code')
        lines = cr.dictfetchall()

        self.localcontext.update( {
            'lines': lines,
        })
        super(bank_statement_balance_report, self).set_context(objects, data, ids, report_type=report_type)

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(bank_statement_balance_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
        })
        self.context = context


class report_bankstatementbalance(osv.AbstractModel):
    _name = 'report.account_bank_statement_extensions.report_bankstatementbalance'
    _inherit = 'report.abstract_report'
    _template = 'account_bank_statement_extensions.report_bankstatementbalance'
    _wrapped_report_class = bank_statement_balance_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
