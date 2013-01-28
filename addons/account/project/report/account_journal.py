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
from openerp.report import report_sxw

#
# Use period and Journal for selection or resources
#
class journal_print(report_sxw.rml_parse):
    def lines(self, journal_id, *args):
        self.cr.execute('select id from account_analytic_line where journal_id=%s order by date,id', (journal_id,))
        ids = map(lambda x: x[0], self.cr.fetchall())
        res = self.pool.get('account.analytic.line').browse(self.cr, self.uid, ids)
        return res
    def _sum_lines(self, journal_id):
        self.cr.execute('select sum(amount) from account_analytic_line where journal_id=%s', (journal_id,))
        return self.cr.fetchone()[0] or 0.0
    def __init__(self, cr, uid, name, context):
        super(journal_print, self).__init__(cr, uid, name, context=context)
        self.localcontext = {
            'time': time,
            'lines': self.lines,
            'sum_lines': self._sum_lines,
        }
report_sxw.report_sxw('report.account.analytic.journal.print', 'account.analytic.journal', 'addons/account/project/report/analytic_journal.rml',parser=journal_print)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

