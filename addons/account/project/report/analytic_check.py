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

import pooler
import time
from report import report_sxw

class account_analytic_analytic_check(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_analytic_analytic_check, self).__init__(cr, uid, name, context=context)
        self.sum_gen_deb = 0.0
        self.sum_gen_cred = 0.0
        self.sum_ana_deb = 0.0
        self.sum_ana_cred = 0.0
        self.localcontext.update( {
            'time': time,
            'lines_p': self._lines_p,
            'general_debit': self._gen_deb,
            'general_credit': self._gen_cred,
            'analytic_debit': self._ana_deb,
            'analytic_credit': self._ana_cred,
            'delta_debit': self._delta_deb,
            'delta_credit': self._delta_cred,
        })
    def _lines_p(self, date1, date2):
        res = []
        acc_obj = self.pool.get('account.account')

        for a in acc_obj.read(self.cr, self.uid, self.ids, ['name', 'code']):
            self.cr.execute("SELECT sum(debit), sum(credit) \
                    FROM account_move_line \
                    WHERE date>=%s AND date<=%s AND state<>'draft' AND account_id = %s", (date1, date2, a['id']))
            (gd, gc) = self.cr.fetchone()
            gd = gd or 0.0
            gc = gc or 0.0

            self.cr.execute("SELECT abs(sum(amount)) AS balance \
                    FROM account_analytic_line \
                    WHERE date>=%s AND date<=%s AND amount<0 AND general_account_id = %s", (date1, date2, a['id']))
            (ad,) = self.cr.fetchone()
            ad = ad or 0.0
            self.cr.execute("SELECT abs(sum(amount)) AS balance \
                    FROM account_analytic_line \
                    WHERE date>=%s AND date<=%s AND amount>0 AND general_account_id = %s", (date1, date2, a['id']))
            (ac,) = self.cr.fetchone()
            ac = ac or 0.0

            res.append({'code': a['code'], 'name': a['name'],
                'gen_debit': gd,
                'gen_credit': gc,
                'ana_debit': ad,
                'ana_credit': ac,
                'delta_debit': gd - ad,
                'delta_credit': gc - ac,})
            self.sum_gen_deb += gd
            self.sum_gen_cred += gc
            self.sum_ana_deb += ad
            self.sum_ana_cred += ac

        return res

    def _gen_deb(self, date1, date2):
        return self.sum_gen_deb

    def _gen_cred(self, date1, date2):
        return self.sum_gen_cred

    def _ana_deb(self, date1, date2):
        return self.sum_ana_deb

    def _ana_cred(self, date1, date2):
        return self.sum_ana_cred

    def _delta_deb(self, date1, date2):
        return (self._gen_deb(date1,date2)-self._ana_deb(date1,date2))

    def _delta_cred(self, date1, date2):
        return (self._gen_cred(date1,date2)-self._ana_cred(date1,date2))

report_sxw.report_sxw('report.account.analytic.account.analytic.check', 'account.analytic.account', 'addons/account/project/report/analytic_check.rml',parser=account_analytic_analytic_check, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
