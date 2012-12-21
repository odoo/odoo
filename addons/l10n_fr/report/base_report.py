# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
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

from openerp.report import report_sxw

class base_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(base_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            '_load': self._load,
            '_get_variable': self._get_variable,
            '_set_variable': self._set_variable,
        })
        self.context = context

    def _load(self, name, form):
        fiscalyear = self.pool.get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear_id'])
        period_ids=self.pool.get('account.period').search(self.cr, self.uid, [('fiscalyear_id', '=', form['fiscalyear_id'])])

        if period_ids:
            self.cr.execute("SELECT MIN(date_start) AS date_start, MAX(date_stop) AS date_stop FROM account_period WHERE id = ANY(%s)", (period_ids,))
            dates = self.cr.dictfetchall()
        else:
            dates = False
        if dates:
            self._set_variable('date_start', dates[0]['date_start'])
            self._set_variable('date_stop', dates[0]['date_stop'])

        self.cr.execute("SELECT l10n_fr_line.code,definition FROM l10n_fr_line LEFT JOIN l10n_fr_report ON l10n_fr_report.id=report_id WHERE l10n_fr_report.code=%s",(name,))
        datas = self.cr.dictfetchall()
        for line in datas:
            self._load_accounts(form,line['code'],eval(line['definition']),fiscalyear,period_ids)

    def _set_variable(self, variable, valeur):
        self.localcontext.update({variable: valeur})

    def _get_variable(self, variable):
        return self.localcontext[variable]

    def _load_accounts(self, form, code, definition, fiscalyear, period_ids):
        accounts = {}
        for x in definition['load']:
            p = x.split(":")
            accounts[p[1]] = [p[0],p[2]]
        sum = 0.0
        if fiscalyear.state != 'done' or not code.startswith('bpcheck'):
            query_params = []
            query_cond = "("
            for account in accounts:
                query_cond += "aa.code LIKE '" + account + "%%' OR "
            query_cond = query_cond[:-4]+")"

            if len(definition['except']) > 0:
                query_cond = query_cond+" and ("
                for account in definition['except']:
                    query_cond += "aa.code NOT LIKE '"+account+"%%' AND "
                query_cond = query_cond[:-5]+")"

            closed_cond = ""
            if fiscalyear.state == 'done':
                closed_cond=" AND (aml.move_id NOT IN (SELECT account_move.id as move_id FROM account_move WHERE period_id = ANY(%s) AND journal_id=(SELECT res_id FROM ir_model_data WHERE name='closing_journal' AND module='l10n_fr')) OR (aa.type != 'income' AND aa.type !='expense'))"
                query_params.append(list(period_ids))

            query = "SELECT aa.code AS code, SUM(debit) as debit, SUM(credit) as credit " \
                " FROM account_move_line aml LEFT JOIN account_account aa ON aa.id=aml.account_id "\
                " WHERE "+query_cond+closed_cond+" AND aml.state='valid' AND aml.period_id = ANY(%s) GROUP BY code"
            query_params.append(list(period_ids))
            self.cr.execute(query, query_params)

            lines =self.cr.dictfetchall()
            for line in lines:
                for account in accounts:
                    if(line["code"].startswith(account)):
                        operator=accounts[account][0]
                        type=accounts[account][1]
                        value=0.0
                        if(type == "S"):
                            value=line["debit"]-line["credit"]
                        elif(type == "D"):
                            value=line["debit"]-line["credit"]
                            if(abs(value)<0.001): value=0.0
                        elif(type == "C"):
                            value=line["credit"]-line["debit"]
                            if(abs(value)<0.001): value=0.0
                        if(operator == '+'):
                            sum += value
                        else:
                            sum -= value
                        break
        self._set_variable(code, sum)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
