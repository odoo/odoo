# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw
import datetime
import operator

class budget_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(budget_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'lines': self.lines,
            'budget_total': self.budget_total,
            'post_total': self.post_total,
            'time': time,
        })

    def post_total(self, post_obj, date1, date2):
        def str2date(date_str):
            return datetime.date.fromtimestamp(time.mktime(time.strptime(date_str, '%Y-%m-%d')))
        def interval(d1str, d2str):
            return (str2date(d2str) - str2date(d1str) + datetime.timedelta(days=1)).days
        prev = reduce(lambda x,d: x + d.amount, post_obj.dotation_ids, 0.0)
        period_days = interval(date1, date2)
        for d in post_obj.dotation_ids:
            i = interval(d.period_id.date_start, d.period_id.date_stop)
        total_days = reduce(lambda x,d: x+interval(d.period_id.date_start, d.period_id.date_stop), post_obj.dotation_ids, 0)
        achievements = reduce(lambda x,l: x+l['achievements'], self.lines(post_obj, date1, date2), 0.0)
        prev_1=1.00
        if total_days<>0.00:
            prev_1=prev * period_days / total_days
        return [{'prev': prev, 'prev_period': prev_1, 'achievements': achievements}]

    def budget_total(self, post_obj, date1, date2):
        res = {'prev': 0.0, 'prev_period': 0.0, 'achievements': 0.0}
        r = self.post_total(post_obj, date1, date2)[0]
        for k in r:
            res[k] += r[k]
        return [res]

    def lines(self, post_obj, date1, date2):
        res = []
        for a in post_obj.account_ids:
            self.cr.execute("SELECT COALESCE(SUM(debit-credit), 0) FROM account_move_line WHERE account_id=%s AND date>=%s AND date<=%s and state<>'draft'", (a.id, date1, date2))
            achievements = float(self.cr.fetchone()[0])
            res.append({'name': a.name, 'code': a.code, 'achievements': achievements})
        return res
report_sxw.report_sxw('report.account.budget', 'account.budget.post', 'addons/account_budget/report/budget_report.rml',parser=budget_report,header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

