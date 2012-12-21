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

class account_statement(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(account_statement, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.localcontext.update({
            'time': time,
            'get_total': self._get_total,
            'get_data': self._get_data,
        })

    def _get_data(self, statement):
        lines = []
        for line in statement.line_ids:
            lines.append(line)

        return lines

    def _get_total(self, statement_line_ids):
        total = 0.0
        for line in statement_line_ids:
            total += line.amount
        return total

report_sxw.report_sxw('report.account.statement', 'account.bank.statement', 'addons/statement/report/account_statement.rml', parser=account_statement,header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
