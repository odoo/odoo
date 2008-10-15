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

import pooler
import time
from report import report_sxw

#
# Use period and Journal for selection or resources
#
class journal_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(journal_print, self).__init__(cr, uid, name, context)
        self.localcontext.update( {
            'time': time,
            'lines': self.lines,
            'periods': self.periods,
            'sum_debit_period': self._sum_debit_period,
            'sum_credit_period': self._sum_credit_period,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit
        })

    def preprocess(self, objects, datas, ids):
        super(journal_print, self).preprocess(objects, datas, ids)
        self.cr.execute('select period_id, journal_id from account_journal_period where id in (' + ','.join([str(id) for id in ids]) + ')')
        res = self.cr.fetchall()
        self.period_ids = ','.join([str(x[0]) for x in res])
        self.journal_ids = ','.join([str(x[1]) for x in res])

    # returns a list of period objs
    def periods(self, journal_period_objs):
        dic = {}
        def filter_unique(o):
            key = o.period_id.id
            res = key in dic
            if not res:
                dic[key] = True
            return not res
        filtered_objs = filter(filter_unique, journal_period_objs)
        return map(lambda x: x.period_id, filtered_objs)
        
    def lines(self, period_id):
        if not self.journal_ids:
            return []
        self.cr.execute('select j.code, j.name, sum(l.debit) as debit, sum(l.credit) as credit from account_move_line l left join account_journal j on (l.journal_id=j.id) where period_id=%d and journal_id in (' + self.journal_ids + ') and l.state<>\'draft\' group by j.id, j.code, j.name', (period_id,))
        return self.cr.dictfetchall()
        
    def _sum_debit_period(self, period_id):
        if not self.journal_ids:
            return 0.0
        self.cr.execute('select sum(debit) from account_move_line where period_id=%d and journal_id in (' + self.journal_ids + ') and state<>\'draft\'', (period_id,))
        return self.cr.fetchone()[0] or 0.0
        
    def _sum_credit_period(self, period_id):
        if not self.journal_ids:
            return 0.0
        self.cr.execute('select sum(credit) from account_move_line where period_id=%d and journal_id in (' + self.journal_ids + ') and state<>\'draft\'', (period_id,))
        return self.cr.fetchone()[0] or 0.0
        
    def _sum_debit(self):
        if not self.journal_ids or not self.period_ids:
            return 0.0
        self.cr.execute('select sum(debit) from account_move_line where period_id in (' + self.period_ids + ') and journal_id in (' + self.journal_ids + ') and state<>\'draft\'')
        return self.cr.fetchone()[0] or 0.0
        
    def _sum_credit(self):
        if not self.journal_ids or not self.period_ids:
            return 0.0
        self.cr.execute('select sum(credit) from account_move_line where period_id in (' + self.period_ids + ') and journal_id in (' + self.journal_ids + ') and state<>\'draft\'')
        return self.cr.fetchone()[0] or 0.0
report_sxw.report_sxw('report.account.general.journal', 'account.journal.period', 'addons/account/report/general_journal.rml',parser=journal_print, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

