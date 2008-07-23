# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
import pooler
from report import report_sxw

class tax_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(tax_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_period': self._get_period,
            'get_codes': self._get_codes,
            'get_general': self._get_general,
            'get_company': self._get_company,
            'get_currency': self._get_currency,
        })

    def _add_header(self, node):
        return True

    def _get_period(self, period_id):
        return self.pool.get('account.period').browse(self.cr, self.uid, period_id).name

    def _get_general(self, tax_code_id, period_id, company_id, based_on):
        res=[]
        if based_on == 'payments':
            self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id \
                    FROM account_move_line AS line, \
                        account_account AS account, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.state<>%s \
                        AND line.period_id = %d \
                        AND line.tax_code_id = %d  \
                        AND line.account_id = account.id \
                        AND account.company_id = %d \
                        AND move.id = line.move_id \
                        AND ((invoice.state = %s) \
                            OR (invoice.id IS NULL))  \
                    GROUP BY account.id', ('draft', period_id, tax_code_id,
                        company_id, 'paid'))
        else :
            self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id \
                    FROM account_move_line AS line, \
                        account_account AS account \
                    WHERE line.state <> %s \
                        AND line.period_id = %d \
                        AND line.tax_code_id = %d  \
                        AND line.account_id = account.id \
                        AND account.company_id = %d \
                        AND account.active \
                    GROUP BY account.id', ('draft', period_id, tax_code_id,
                        company_id))
        res = self.cr.dictfetchall()
        i = 0
        while i<len(res):
            res[i]['account'] = self.pool.get('account.account').browse(self.cr, self.uid, res[i]['account_id'])
            i+=1
        return res

    def _get_codes(self, period_id, based_on, parent=False, level=0):
        tc = self.pool.get('account.tax.code')
        ids = tc.search(self.cr, self.uid, [('parent_id','=',parent)])
        res = []
        for code in tc.browse(self.cr, self.uid, ids, {'period_id': period_id,
            'based_on': based_on}):
            res.append((' - '*level*2, code))
            res += self._get_codes(period_id, based_on, code.id, level+1)
        return res

    def _get_company(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

    def _get_currency(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name

report_sxw.report_sxw('report.account.vat.declaration', 'account.tax.code',
    'addons/account/report/tax_report.rml', parser=tax_report, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

