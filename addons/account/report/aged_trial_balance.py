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
from operator import itemgetter
import pooler
import rml_parse
from report import report_sxw

class aged_trial_report(rml_parse.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(aged_trial_report, self).__init__(cr, uid, name, context=context)
        self.line_query = ''
        self.total_account = []


        self.localcontext.update({
            'time': time,
            'get_lines': self._get_lines,
            'get_total': self._get_total,
            'get_direction': self._get_direction,
            'get_for_period': self._get_for_period,
            'get_company': self._get_company,
            'get_currency': self._get_currency,

        })


    def _get_lines(self, form):

        if (form['result_selection'] == 'customer' ):
            self.ACCOUNT_TYPE = ('receivable', )
        elif (form['result_selection'] == 'supplier'):
            self.ACCOUNT_TYPE = ('payable', )
        else:
            self.ACCOUNT_TYPE = ('payable', 'receivable')


        res = []
        account_move_line_obj = pooler.get_pool(self.cr.dbname).get('account.move.line')
        self.line_query = account_move_line_obj._query_get(self.cr, self.uid, obj='line',
                context={'fiscalyear': form['fiscalyear']})
        self.cr.execute("""SELECT DISTINCT res_partner.id AS id,
                    res_partner.name AS name
                FROM res_partner,account_move_line AS line, account_account
                WHERE (line.account_id=account_account.id)
                    AND ((reconcile_id IS NULL)
                    OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))
                    AND (line.partner_id=res_partner.id)
                    AND (account_account.company_id = %s)
                ORDER BY res_partner.name""",
                (form['date1'], form['company_id']))
        partners = self.cr.dictfetchall()
        ## mise a 0 du total
        for i in range(7):
            self.total_account.append(0)

        partner_ids = tuple(map(itemgetter('id'), partners))
        # This dictionary will store the debit-credit for all partners, using partner_id as key.
        totals = {}
        self.cr.execute("""SELECT partner_id, SUM(debit-credit)
                    FROM account_move_line AS line, account_account
                    WHERE (line.account_id = account_account.id)
                    AND (account_account.type IN %s)
                    AND (partner_id in %s)
                    AND ((reconcile_id IS NULL)
                    OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))
                    AND (account_account.company_id = %s)
                    AND account_account.active
                    GROUP BY partner_id""" , (
                        self.ACCOUNT_TYPE, partner_ids,
                        form['date1'], form['company_id']))
        t = self.cr.fetchall()
        for i in t:
            totals[i[0]] = i[1]

        # This dictionary will store the future or past of all partners
        future_past = {}
        if form['direction_selection'] == 'future':
            self.cr.execute("""SELECT partner_id, SUM(debit-credit)
                        FROM account_move_line AS line, account_account
                        WHERE (line.account_id=account_account.id)
                        AND (account_account.type IN %s)
                        AND (COALESCE(date_maturity,date) < %s)
                        AND (partner_id in %s)
                        AND ((reconcile_id IS NULL)
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))
                        AND (account_account.company_id = %s)
                        AND account_account.active
                        GROUP BY partner_id""", (
                self.ACCOUNT_TYPE, form['date1'], partner_ids,
                form['date1'], form['company_id']))
            t = self.cr.fetchall()
            for i in t:
                future_past[i[0]] = i[1]
        elif form['direction_selection'] == 'past': # Using elif so people could extend without this breaking
            self.cr.execute("""SELECT partner_id, SUM(debit-credit)
                    FROM account_move_line AS line, account_account
                    WHERE (line.account_id=account_account.id)
                        AND (account_account.type IN %s)
                        AND (COALESCE(date_maturity,date) > %s)
                        AND (partner_id in %s)
                        AND ((reconcile_id IS NULL)
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))
                        AND (account_account.company_id = %s)
                        AND account_account.active
                        GROUP BY partner_id""" , (
                self.ACCOUNT_TYPE, form['date1'], partner_ids,
                form['date1'], form['company_id']))
            t = self.cr.fetchall()
            for i in t:
                future_past[i[0]] = i[1]

        # Use one query per period and store results in history (a list variable)
        # Each history will contain : history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            self.cr.execute("""SELECT partner_id, SUM(debit-credit)
                    FROM account_move_line AS line, account_account
                    WHERE (line.account_id=account_account.id)
                        AND (account_account.type IN %s)
                        AND (COALESCE(date_maturity,date) BETWEEN %s AND %s)
                        AND (partner_id in %s )
                        AND ((reconcile_id IS NULL)
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))
                        AND (account_account.company_id = %s)
                        AND account_account.active
                    GROUP BY partner_id""" , (
                self.ACCOUNT_TYPE, form[str(i)]['start'], form[str(i)]['stop'],
                partner_ids ,form['date1'] ,form['company_id']))

            t = self.cr.fetchall()
            d = {}
            for i in t:
                d[i[0]] = i[1]
            history.append(d)

        for partner in partners:
            values = {}
            ## If choise selection is in the future
            if form['direction_selection'] == 'future':
                # Query here is replaced by one query which gets the all the partners their 'before' value
                before = False
                if future_past.has_key(partner['id']):
                    before = [ future_past[partner['id']] ]

                self.total_account[6] = self.total_account[6] + (before and before[0] or 0.0)

                values['direction'] = before and before[0] or 0.0
            elif form['direction_selection'] == 'past': # Changed this so people could in the future create new direction_selections
                # Query here is replaced by one query which gets the all the partners their 'after' value
                after = False
                if future_past.has_key(partner['id']): # Making sure this partner actually was found by the query
                    after = [ future_past[partner['id']] ]

                self.total_account[6] = self.total_account[6] + (after and after[0] or 0.0)
                values['direction'] = after and after[0] or ""

            for i in range(5):
                during = False
                if history[i].has_key(partner['id']):
                    during = [ history[i][partner['id']] ]
                # Ajout du compteur
                self.total_account[(i)] = self.total_account[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or ""

            total = False
            if totals.has_key( partner['id'] ):
                total = [ totals[partner['id']] ]
            values['total'] = total and total[0] or 0.0
            ## Add for total
            self.total_account[(i+1)] = self.total_account[(i+1)] + (total and total[0] or 0.0)
            values['name'] = partner['name']
            #t = 0.0
            #for i in range(5)+['direction']:
            #   t+= float(values.get(str(i), 0.0) or 0.0)
            #values['total'] = t

            if values['total']:
                res.append(values)

        total = 0.0
        totals = {}
        for r in res:
            total += float(r['total'] or 0.0)
            for i in range(5)+['direction']:
                totals.setdefault(str(i), 0.0)
                totals[str(i)] += float(r[str(i)] or 0.0)
        return res

    def _get_total(self,pos):
        period = self.total_account[int(pos)]
        return period

    def _get_direction(self,pos):
        period = self.total_account[int(pos)]
        return period

    def _get_for_period(self,pos):
        period = self.total_account[int(pos)]
        return period

    def _get_company(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

    def _get_currency(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name


report_sxw.report_sxw('report.account.aged_trial_balance', 'res.partner',
        'addons/account/report/aged_trial_balance.rml',parser=aged_trial_report,header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
