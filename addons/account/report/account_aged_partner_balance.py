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

import pooler
import rml_parse
from report import report_sxw
from common_report_header import common_report_header

class aged_trial_report(rml_parse.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context):
        super(aged_trial_report, self).__init__(cr, uid, name, context=context)
        self.query_line = ''
        self.total_account = []
        self.localcontext.update({
            'time': time,
            'get_lines_with_out_partner': self._get_lines_with_out_partner,
            'get_lines': self._get_lines,
            'get_total': self._get_total,
            'get_direction': self._get_direction,
            'get_for_period': self._get_for_period,
            'get_company': self._get_company,
            'get_currency': self._get_currency,
            'get_partners':self._get_partners,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
        })

    def set_context(self, objects, data, ids, report_type=None):
        self.query = data['form'].get('query_line', '')
        self.direction_selection = data['form'].get('direction_selection', 'past')
        self.target_move = data['form'].get('direction_selection', 'past')
        self.date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        if (data['form']['result_selection'] == 'customer' ):
            self.ACCOUNT_TYPE = ['receivable']
        elif (data['form']['result_selection'] == 'supplier'):
            self.ACCOUNT_TYPE = ['payable']
        else:
            self.ACCOUNT_TYPE = ['payable','receivable']
        return super(aged_trial_report, self).set_context(objects, data, ids, report_type=report_type)

    def _get_lines(self, form):
        res = []
        account_move_line_obj = pooler.get_pool(self.cr.dbname).get('account.move.line')
        self.cr.execute('SELECT DISTINCT res_partner.id AS id,\
                    res_partner.name AS name \
                FROM res_partner,account_move_line AS l, account_account\
                WHERE (l.account_id=account_account.id)\
                    AND ((reconcile_id IS NULL)\
                    OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                    AND (l.partner_id=res_partner.id)\
                    AND ' + self.query + ' \
                ORDER BY res_partner.name' , (self.date_from,))
        partners = self.cr.dictfetchall()
        ## mise a 0 du total
        for i in range(7):
            self.total_account.append(0)
        #
        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [x['id'] for x in partners]

        # This dictionary will store the debit-credit for all partners, using partner_id as key.
        totals = {}
        self.cr.execute('SELECT partner_id, SUM(debit-credit) \
                    FROM account_move_line AS l, account_account\
                    WHERE (l.account_id = account_account.id)\
                    AND (account_account.type IN %s)\
                    AND (partner_id IN %s)\
                    AND ((reconcile_id IS NULL)\
                    OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                    AND ' + self.query + '\
                    AND account_account.active\
                    GROUP BY partner_id ' , (tuple(self.ACCOUNT_TYPE), tuple(partner_ids), self.date_from,))
        t = self.cr.fetchall()
        for i in t:
            totals[i[0]] = i[1]

        # This dictionary will store the future or past of all partners
        future_past = {}
        if self.direction_selection == 'future':
            self.cr.execute('SELECT partner_id, SUM(debit-credit) \
                        FROM account_move_line AS l, account_account\
                        WHERE (l.account_id=account_account.id)\
                        AND (account_account.type IN %s)\
                        AND (COALESCE(date_maturity, date) < %s)\
                        AND (partner_id IN %s)\
                        AND ((reconcile_id IS NULL)\
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                        AND '+ self.query + '\
                        AND account_account.active\
                        GROUP BY partner_id', (tuple(self.ACCOUNT_TYPE), self.date_from, tuple(partner_ids),self.date_from,))
            t = self.cr.fetchall()
            for i in t:
                future_past[i[0]] = i[1]
        elif self.direction_selection == 'past': # Using elif so people could extend without this breaking
            self.cr.execute('SELECT partner_id, SUM(debit-credit) \
                    FROM account_move_line AS l, account_account\
                    WHERE (l.account_id=account_account.id)\
                        AND (account_account.type IN %s)\
                        AND (COALESCE(date_maturity,date) > %s)\
                        AND (partner_id IN %s)\
                        AND ((reconcile_id IS NULL)\
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                        AND '+ self.query + '\
                        AND account_account.active\
                        GROUP BY partner_id' , (tuple(self.ACCOUNT_TYPE), self.date_from, tuple(partner_ids), self.date_from,))
            t = self.cr.fetchall()
            for i in t:
                future_past[i[0]] = i[1]

        # Use one query per period and store results in history (a list variable)
        # Each history will contain : history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            args_list = (tuple(self.ACCOUNT_TYPE), tuple(partner_ids) ,self.date_from,)
            dates_query = '(COALESCE(date_maturity,date)'
            if form[str(i)]['start'] and form[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (form[str(i)]['start'], form[str(i)]['stop'])
            elif form[str(i)]['start']:
                dates_query += ' > %s)'
                args_list += (form[str(i)]['start'],)
            else:
                dates_query += ' < %s)'
                args_list += (form[str(i)]['stop'],)
            self.cr.execute('SELECT partner_id, SUM(debit-credit)\
                    FROM account_move_line AS l, account_account\
                    WHERE (l.account_id = account_account.id)\
                        AND (account_account.type IN %s)\
                        AND (partner_id IN %s)\
                        AND ((reconcile_id IS NULL)\
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                        AND '+ self.query + '\
                        AND account_account.active\
                        AND ' + dates_query + '\
                    GROUP BY partner_id' , args_list)
            t = self.cr.fetchall()
            d = {}
            for i in t:
                d[i[0]] = i[1]
            history.append(d)

        for partner in partners:
            values = {}
            ## If choise selection is in the future
            if self.direction_selection == 'future':
                # Query here is replaced by one query which gets the all the partners their 'before' value
                before = False
                if future_past.has_key(partner['id']):
                    before = [ future_past[partner['id']] ]
                self.total_account[6] = self.total_account[6] + (before and before[0] or 0.0)
                values['direction'] = before and before[0] or 0.0
            elif self.direction_selection == 'past': # Changed this so people could in the future create new direction_selections
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

    def _get_lines_with_out_partner(self, form):
        res = []
        account_move_line_obj = pooler.get_pool(self.cr.dbname).get('account.move.line')
        ## mise a 0 du total
        for i in range(7):
            self.total_account.append(0)
        totals = {}
        self.cr.execute('SELECT SUM(debit-credit) \
                    FROM account_move_line AS l, account_account\
                    WHERE (l.account_id = account_account.id)\
                    AND (l.partner_id IS NULL)\
                    AND (account_account.type IN %s)\
                    AND ((reconcile_id IS NULL) \
                    OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                    AND ' + self.query + '\
                    AND account_account.active ' ,(tuple(self.ACCOUNT_TYPE), self.date_from, ))
        t = self.cr.fetchall()
        for i in t:
            totals['No Partner Defined'] = i[0]
        future_past = {}
        if self.direction_selection == 'future':
            self.cr.execute('SELECT SUM(debit-credit) \
                        FROM account_move_line AS l, account_account\
                        WHERE (l.account_id=account_account.id)\
                        AND (l.partner_id IS NULL)\
                        AND (account_account.type IN %s)\
                        AND (COALESCE(date_maturity, date) < %s)\
                        AND ((reconcile_id IS NULL)\
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                        AND '+ self.query + '\
                        AND account_account.active ', (tuple(self.ACCOUNT_TYPE), self.date_from, self.date_from, ))
            t = self.cr.fetchall()
            for i in t:
                future_past['No Partner Defined'] = i[0]
        elif self.direction_selection == 'past': # Using elif so people could extend without this breaking
            self.cr.execute('SELECT SUM(debit-credit) \
                    FROM account_move_line AS l, account_account\
                    WHERE (l.account_id=account_account.id)\
                        AND (l.partner_id IS NULL)\
                        AND (account_account.type IN %s)\
                        AND (COALESCE(date_maturity,date) > %s)\
                        AND ((reconcile_id IS NULL)\
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                        AND '+ self.query + '\
                        AND account_account.active ' , (tuple(self.ACCOUNT_TYPE), self.date_from, self.date_from,))
            t = self.cr.fetchall()
            for i in t:
                future_past['No Partner Defined'] = i[0]
        history = []
        for i in range(5):
            self.cr.execute('SELECT SUM(debit-credit)\
                    FROM account_move_line AS l, account_account\
                    WHERE (l.account_id = account_account.id)\
                        AND (l.partner_id IS NULL)\
                        AND (account_account.type IN %s)\
                        AND (COALESCE(date_maturity,date) BETWEEN %s AND %s)\
                        AND ((reconcile_id IS NULL)\
                        OR (reconcile_id IN (SELECT recon.id FROM account_move_reconcile AS recon WHERE recon.create_date > %s )))\
                        AND '+ self.query + '\
                        AND account_account.active ' , (tuple(self.ACCOUNT_TYPE), form[str(i)]['start'], form[str(i)]['stop'], self.date_from,))
            t = self.cr.fetchall()
            d = {}
            for i in t:
                d['No Partner Defined'] = i[0]
            history.append(d)

        values = {}
        if self.direction_selection == 'future':
            before = False
            if future_past.has_key('No Partner Defined'):
                before = [ future_past['No Partner Defined'] ]
            self.total_account[6] = self.total_account[6] + (before and before[0] or 0.0)
            values['direction'] = before and before[0] or 0.0
        elif self.direction_selection == 'past':
            after = False
            if future_past.has_key('No Partner Defined'):
                after = [ future_past['No Partner Defined'] ]
            self.total_account[6] = self.total_account[6] + (after and after[0] or 0.0)
            values['direction'] = after and after[0] or ""

        for i in range(5):
            during = False
            if history[i].has_key('No Partner Defined'):
                during = [ history[i]['No Partner Defined'] ]
            self.total_account[(i)] = self.total_account[(i)] + (during and during[0] or 0)
            values[str(i)] = during and during[0] or ""

        total = False
        if totals.has_key( 'No Partner Defined' ):
            total = [ totals['No Partner Defined'] ]
        values['total'] = total and total[0] or 0.0
        ## Add for total
        self.total_account[(i+1)] = self.total_account[(i+1)] + (total and total[0] or 0.0)
        values['name'] = 'No Partner Defined'

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

    def _get_partners(self,data):
        if data['form']['result_selection'] == 'customer':
            return 'Receivable Accounts'
        elif data['form']['result_selection'] == 'supplier':
            return 'Payable Accounts'
        elif data['form']['result_selection'] == 'customer_supplier':
            return 'Receivable and Payable Accounts'
        return ''

report_sxw.report_sxw('report.account.aged_trial_balance', 'res.partner',
        'addons/account/report/account_aged_partner_balance.rml',parser=aged_trial_report, header="internal landscape")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
