# -*- coding: utf-8 -*-

import time
from openerp import api, models
from common_report_header import CommonReportHeader


class ReportAgedPartnerBalance(models.AbstractModel, CommonReportHeader):

    _name = 'report.account.report_agedpartnerbalance'

    def _get_lines(self, form):
        res = []
        self.total_account = []
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        self._cr.execute('SELECT DISTINCT res_partner.id AS id,\
                    res_partner.name AS name \
                FROM res_partner,account_move_line AS l, account_account, account_move am\
                WHERE (l.account_id=account_account.id) \
                    AND (l.move_id=am.id) \
                    AND (am.state IN %s)\
                    AND (account_account.internal_type IN %s)\
                    AND l.reconciled IS FALSE\
                    AND (l.partner_id=res_partner.id)\
                    AND (l.date <= %s)\
                ORDER BY res_partner.name', (tuple(move_state), tuple(self.ACCOUNT_TYPE), self.date_from))

        partners = self._cr.dictfetchall()
        # mise a 0 du total
        for i in range(7):
            self.total_account.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['id'] for partner in partners]
        if not partner_ids:
            return []

        # This dictionary will store the debit-credit for all partners, using partner_id as key.
        totals = {}
        self._cr.execute('SELECT l.partner_id, SUM(l.debit-l.credit) \
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id = account_account.id) AND (l.move_id=am.id) \
                    AND (am.state IN %s)\
                    AND (account_account.internal_type IN %s)\
                    AND (l.partner_id IN %s)\
                    AND (l.date <= %s)\
                    GROUP BY l.partner_id ', (tuple(move_state), tuple(self.ACCOUNT_TYPE), tuple(partner_ids), self.date_from,))
        partner_totals = self._cr.fetchall()
        for partner_id, amount in partner_totals:
            totals[partner_id] = amount

        # This dictionary will store the future or past of all partners
        future_past = {}
        if self.direction_selection == 'future':
            self._cr.execute('SELECT l.partner_id, SUM(l.debit-l.credit) \
                        FROM account_move_line AS l, account_account, account_move am \
                        WHERE (l.account_id=account_account.id) AND (l.move_id=am.id) \
                        AND (am.state IN %s)\
                        AND (account_account.internal_type IN %s)\
                        AND (COALESCE(l.date_maturity, l.date) < %s)\
                        AND (l.partner_id IN %s)\
                        AND l.reconciled IS FALSE\
                    AND (l.date <= %s)\
                        GROUP BY l.partner_id', (tuple(move_state), tuple(self.ACCOUNT_TYPE), self.date_from, tuple(partner_ids),self.date_from,))
            partner_totals = self._cr.fetchall()
            for partner_id, amount in partner_totals:
                future_past[partner_id] = amount
        elif self.direction_selection == 'past': # Using elif so people could extend without this breaking
            self._cr.execute('SELECT l.partner_id, SUM(l.debit-l.credit) \
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id=account_account.id) AND (l.move_id=am.id)\
                        AND (am.state IN %s)\
                        AND (account_account.internal_type IN %s)\
                        AND (COALESCE(l.date_maturity,l.date) > %s)\
                        AND (l.partner_id IN %s)\
                        AND l.reconciled IS FALSE\
                    AND (l.date <= %s)\
                        GROUP BY l.partner_id', (tuple(move_state), tuple(self.ACCOUNT_TYPE), self.date_from, tuple(partner_ids), self.date_from,))
            partner_totals = self._cr.fetchall()
            for partner_id, amount in partner_totals:
                future_past[partner_id] = amount

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []

        for i in range(5):
            args_list = (tuple(move_state), tuple(self.ACCOUNT_TYPE), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if form[str(i)]['start'] and form[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (form[str(i)]['start'], form[str(i)]['stop'])
            elif form[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (form[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (form[str(i)]['stop'],)
            args_list += (self.date_from,)

            self._cr.execute('''SELECT l.partner_id, SUM(l.debit-l.credit), l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id=am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND (l.partner_id IN %s)
                        AND l.reconciled IS FALSE
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    GROUP BY l.partner_id, l.id''', args_list)
            partners_partial = self._cr.fetchall()
            partners_amount = dict((partner_id, 0) for partner_id, amount, line_id in partners_partial)

            for partner_id, amount, line_id in partners_partial:
                partial_reconcile_ids = []
                line = self.env['account.move.line'].browse(line_id)
                for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                    if not partial_line.credit_move_id.id in partial_reconcile_ids:
                        partial_reconcile_ids.append(partial_line.credit_move_id.id)
                    if not partial_line.debit_move_id.id in partial_reconcile_ids:
                        partial_reconcile_ids.append(partial_line.debit_move_id.id)
                if partial_reconcile_ids:
                    # in case of partial reconciliation, we want to keep the left amount in the oldest period
                    self._cr.execute('''SELECT MIN(COALESCE(date_maturity,date)) from account_move_line where id = %s''', (line_id,))
                    date = self._cr.fetchall()
                    partial = False
                    if 'BETWEEN' in dates_query:
                        partial = date and args_list[-3] <= date[0][0] <= args_list[-2]
                    elif '>=' in dates_query:
                        partial = date and date[0][0] >= form[str(i)]['start']
                    else:
                        partial = date and date[0][0] <= form[str(i)]['stop']
                    if partial:
                        # partial reconcilation
                        limit_date = 'COALESCE(l.date_maturity,l.date) %s %%s' % ('<=' if self.direction_selection == 'past' else '>=')
                        self._cr.execute('''SELECT SUM(l.debit-l.credit)
                                           FROM account_move_line AS l, account_move AS am
                                           WHERE l.move_id = am.id AND am.state in %s
                                           AND l.id in %s
                                           AND ''' + limit_date, (tuple(move_state), tuple(partial_reconcile_ids), self.date_from))
                        unreconciled_amount = self._cr.fetchall()
                        partners_amount[partner_id] += unreconciled_amount[0][0]
                else:
                    partners_amount[partner_id] += amount
            history.append(partners_amount)

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
                values['direction'] = after and after[0] or 0.0

            for i in range(5):
                during = False
                if history[i].has_key(partner['id']):
                    during = [ history[i][partner['id']] ]
                # Ajout du compteur
                self.total_account[(i)] = self.total_account[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
            total = False
            if totals.has_key( partner['id'] ):
                total = [ totals[partner['id']] ]
            values['total'] = total and total[0] or 0.0
            ## Add for total
            self.total_account[(i+1)] = self.total_account[(i+1)] + (total and total[0] or 0.0)
            values['name'] = partner['name']

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
        self.total_account = []
        res = []
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        ## mise a 0 du total
        for i in range(7):
            self.total_account.append(0)
        totals = {}
        self._cr.execute('SELECT SUM(l.debit-l.credit) \
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id = account_account.id) AND (l.move_id=am.id)\
                    AND (am.state IN %s)\
                    AND (l.partner_id IS NULL)\
                    AND (account_account.internal_type IN %s)\
                    AND l.reconciled IS FALSE \
                    AND (l.date <= %s)\
                    ',(tuple(move_state), tuple(self.ACCOUNT_TYPE), self.date_from,))
        total_amount = self._cr.fetchall()
        for amount in total_amount:
            totals['Unknown Partner'] = amount[0]
        future_past = {}
        if self.direction_selection == 'future':
            self._cr.execute('SELECT SUM(l.debit-l.credit) \
                        FROM account_move_line AS l, account_account, account_move am\
                        WHERE (l.account_id=account_account.id) AND (l.move_id=am.id)\
                        AND (am.state IN %s)\
                        AND (l.partner_id IS NULL)\
                        AND (account_account.internal_type IN %s)\
                        AND (COALESCE(l.date_maturity, l.date) < %s)\
                        AND l.reconciled IS FALSE'
                        , (tuple(move_state), tuple(self.ACCOUNT_TYPE), self.date_from,))
            total_amount = self._cr.fetchall()
            for amount in total_amount:
                future_past['Unknown Partner'] = amount[0]
        elif self.direction_selection == 'past': # Using elif so people could extend without this breaking
            self._cr.execute('SELECT SUM(l.debit-l.credit) \
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id=account_account.id) AND (l.move_id=am.id)\
                        AND (am.state IN %s)\
                        AND (l.partner_id IS NULL)\
                        AND (account_account.internal_type IN %s)\
                        AND (COALESCE(l.date_maturity,l.date) > %s)\
                        AND l.reconciled IS FALSE\
                        ', (tuple(move_state), tuple(self.ACCOUNT_TYPE), self.date_from,))
            total_amount = self._cr.fetchall()
            for amount in total_amount:
                future_past['Unknown Partner'] = amount[0]
        history = []

        for i in range(5):
            args_list = (tuple(move_state), tuple(self.ACCOUNT_TYPE))
            dates_query = '(COALESCE(l.date_maturity,l.date)'
            if form[str(i)]['start'] and form[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (form[str(i)]['start'], form[str(i)]['stop'])
            elif form[str(i)]['start']:
                dates_query += ' > %s)'
                args_list += (form[str(i)]['start'],)
            else:
                dates_query += ' < %s)'
                args_list += (form[str(i)]['stop'],)
            args_list += (self.date_from,)
            self._cr.execute('SELECT SUM(l.debit-l.credit)\
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id = account_account.id) AND (l.move_id=am.id)\
                        AND (am.state IN %s)\
                        AND (account_account.internal_type IN %s)\
                        AND (l.partner_id IS NULL)\
                        AND l.reconciled IS FALSE\
                        AND ' + dates_query + '\
                    AND (l.date <= %s)\
                    GROUP BY l.partner_id', args_list)
            total_amount = self._cr.fetchall()
            history_data = {}
            for amount in total_amount:
                history_data['Unknown Partner'] = amount[0]
            history.append(history_data)

        values = {}
        if self.direction_selection == 'future':
            before = False
            if future_past.has_key('Unknown Partner'):
                before = [ future_past['Unknown Partner'] ]
            self.total_account[6] = self.total_account[6] + (before and before[0] or 0.0)
            values['direction'] = before and before[0] or 0.0
        elif self.direction_selection == 'past':
            after = False
            if future_past.has_key('Unknown Partner'):
                after = [ future_past['Unknown Partner'] ]
            self.total_account[6] = self.total_account[6] + (after and after[0] or 0.0)
            values['direction'] = after and after[0] or 0.0

        for i in range(5):
            during = False
            if history[i].has_key('Unknown Partner'):
                during = [ history[i]['Unknown Partner'] ]
            self.total_account[(i)] = self.total_account[(i)] + (during and during[0] or 0)
            values[str(i)] = during and during[0] or 0.0

        total = False
        if totals.has_key( 'Unknown Partner' ):
            total = [ totals['Unknown Partner'] ]
        values['total'] = total and total[0] or 0.0
        ## Add for total
        self.total_account[(i+1)] = self.total_account[(i+1)] + (total and total[0] or 0.0)
        values['name'] = 'Unknown Partner'

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

    def _get_direction(self,pos):
        period = self.total_account[int(pos)]
        return period or 0.0

    def _get_for_period(self, pos):
        period = self.total_account[int(pos)]
        return period or 0.0

    @api.multi
    def render_html(self, data):
        self.total_account = []
        self.model = self._context.get('active_model')
        MoveLine = self.env['account.move.line']
        docs = self.env[self.model].browse(self._context.get('active_id'))

        self.direction_selection = data['options']['form'].get('direction_selection', 'past')
        self.target_move = data['options']['form'].get('target_move', 'all')
        self.date_from = data['options']['form'].get('date_from', time.strftime('%Y-%m-%d'))

        if (data['options']['form']['result_selection'] == 'customer' ):
            self.ACCOUNT_TYPE = ['receivable']
        elif (data['options']['form']['result_selection'] == 'supplier'):
            self.ACCOUNT_TYPE = ['payable']
        else:
            self.ACCOUNT_TYPE = ['payable','receivable']

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['options']['form'],
            'docs': docs,
            'time': time,
            'get_lines_with_out_partner': self._get_lines_with_out_partner,
            'get_lines': self._get_lines,
            'get_direction': self._get_direction,
            'get_for_period': self._get_for_period,
            'get_target_move': self._get_target_move,
        }
        return self.env['report'].render('account.report_agedpartnerbalance', docargs)
