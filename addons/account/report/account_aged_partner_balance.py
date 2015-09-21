# -*- coding: utf-8 -*-

import time
from openerp import api, models


class ReportAgedPartnerBalance(models.AbstractModel):

    _name = 'report.account.report_agedpartnerbalance'

    def _get_partner_move_lines(self, form, account_type, date_from, target_move):
        res = []
        self.total_account = []
        cr = self.env.cr
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        cr.execute('SELECT DISTINCT res_partner.id AS id,\
                    res_partner.name AS name \
                FROM res_partner,account_move_line AS l, account_account, account_move am\
                WHERE (l.account_id = account_account.id) \
                    AND (l.move_id = am.id) \
                    AND (am.state IN %s)\
                    AND (account_account.internal_type IN %s)\
                    AND l.reconciled IS FALSE\
                    AND (l.partner_id = res_partner.id)\
                    AND (l.date <= %s)\
                ORDER BY res_partner.name', (tuple(move_state), tuple(account_type), date_from))

        partners = cr.dictfetchall()
        # put a total of 0
        for i in range(7):
            self.total_account.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['id'] for partner in partners]
        if not partner_ids:
            return []

        # This dictionary will store the debit-credit for all partners, using partner_id as key.
        totals = {}
        cr.execute('SELECT l.partner_id, SUM(l.debit-l.credit) \
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id) \
                    AND (am.state IN %s)\
                    AND (account_account.internal_type IN %s)\
                    AND (l.partner_id IN %s)\
                    AND (l.date <= %s)\
                    GROUP BY l.partner_id ', (tuple(move_state), tuple(account_type), tuple(partner_ids), date_from,))
        partner_totals = cr.fetchall()
        for partner_id, amount in partner_totals:
            totals[partner_id] = amount

        # This dictionary will store the future or past of all partners
        future_past = {}
        cr.execute('SELECT l.partner_id, SUM(l.debit - l.credit) \
                FROM account_move_line AS l, account_account, account_move am \
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)\
                    AND (am.state IN %s)\
                    AND (account_account.internal_type IN %s)\
                    AND (COALESCE(l.date_maturity,l.date) > %s)\
                    AND (l.partner_id IN %s)\
                    AND l.reconciled IS FALSE\
                AND (l.date <= %s)\
                    GROUP BY l.partner_id', (tuple(move_state), tuple(account_type), date_from, tuple(partner_ids), date_from,))
        partner_totals = cr.fetchall()
        for partner_id, amount in partner_totals:
            future_past[partner_id] = amount

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
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
            args_list += (date_from,)

            cr.execute('''SELECT l.partner_id, SUM(l.debit - l.credit), l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND (l.partner_id IN %s)
                        AND l.reconciled IS FALSE
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    GROUP BY l.partner_id, l.id''', args_list)
            partners_partial = cr.fetchall()
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
                    cr.execute('''SELECT MIN(COALESCE(date_maturity, date)) from account_move_line where id = %s''', (line_id,))
                    date = cr.fetchall()
                    partial = False
                    if 'BETWEEN' in dates_query:
                        partial = date and args_list[-3] <= date[0][0] <= args_list[-2]
                    elif '>=' in dates_query:
                        partial = date and date[0][0] >= form[str(i)]['start']
                    else:
                        partial = date and date[0][0] <= form[str(i)]['stop']
                    if partial:
                        # partial reconcilation
                        limit_date = 'COALESCE(l.date_maturity, l.date) <= %s'
                        cr.execute('''SELECT SUM(l.debit - l.credit)
                                           FROM account_move_line AS l, account_move AS am
                                           WHERE l.move_id = am.id AND am.state IN %s
                                           AND l.id IN %s
                                           AND ''' + limit_date, (tuple(move_state), tuple(partial_reconcile_ids), date_from))
                        unreconciled_amount = cr.fetchall()
                        partners_amount[partner_id] += unreconciled_amount[0][0]
                else:
                    partners_amount[partner_id] += amount
            history.append(partners_amount)

        for partner in partners:
            values = {}
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
                # Adding counter
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

    def _get_move_lines_with_out_partner(self, form, account_type, date_from, target_move):
        res = []
        cr = self.env.cr
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']

        ## put a total of 0
        for i in range(7):
            self.total_account.append(0)
        totals = {}
        cr.execute('SELECT SUM(l.debit - l.credit) \
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)\
                    AND (am.state IN %s)\
                    AND (l.partner_id IS NULL)\
                    AND (account_account.internal_type IN %s)\
                    AND l.reconciled IS FALSE \
                    AND (l.date <= %s)\
                    ',(tuple(move_state), tuple(account_type), date_from,))
        total_amount = cr.fetchall()
        for amount in total_amount:
            totals['Unknown Partner'] = amount[0]
        future_past = {}
        cr.execute('SELECT SUM(l.debit-l.credit) \
                FROM account_move_line AS l, account_account, account_move am \
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)\
                    AND (am.state IN %s)\
                    AND (l.partner_id IS NULL)\
                    AND (account_account.internal_type IN %s)\
                    AND (COALESCE(l.date_maturity,l.date) > %s)\
                    AND l.reconciled IS FALSE\
                    ', (tuple(move_state), tuple(account_type), date_from,))
        total_amount = cr.fetchall()
        for amount in total_amount:
            future_past['Unknown Partner'] = amount[0]

        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type))
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
            args_list += (date_from,)
            cr.execute('SELECT SUM(l.debit - l.credit)\
                    FROM account_move_line AS l, account_account, account_move am \
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)\
                        AND (am.state IN %s)\
                        AND (account_account.internal_type IN %s)\
                        AND (l.partner_id IS NULL)\
                        AND l.reconciled IS FALSE\
                        AND ' + dates_query + '\
                    AND (l.date <= %s)\
                    GROUP BY l.partner_id', args_list)
            total_amount = cr.fetchall()
            history_data = {}
            for amount in total_amount:
                history_data['Unknown Partner'] = amount[0]
            history.append(history_data)

        values = {}
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

    @api.multi
    def render_html(self, data):
        self.total_account = []
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        target_move = data['form'].get('target_move', 'all')
        date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))

        if data['form']['result_selection'] == 'customer':
            account_type = ['receivable']
        elif data['form']['result_selection'] == 'supplier':
            account_type = ['payable']
        else:
            account_type = ['payable','receivable']

        without_partner_movelines = self._get_move_lines_with_out_partner(data['form'], account_type, date_from, target_move)
        partner_movelines = self._get_partner_move_lines(data['form'], account_type, date_from, target_move)
        movelines = partner_movelines + without_partner_movelines
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_partner_lines': movelines,
            'get_direction': self.total_account,
        }
        return self.env['report'].render('account.report_agedpartnerbalance', docargs)
