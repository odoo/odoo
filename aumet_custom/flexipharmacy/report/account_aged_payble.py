# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero


class AgedPayablePdf(models.AbstractModel):
    _name = 'report.flexipharmacy.aged_payble_template'
    _description = 'Report Aged Payable Pdf'

    def _get_partner_move_lines_custom(self, account_type, date_from, target_move, period_length):
        periods = {}
        start = datetime.strptime(date_from, "%Y-%m-%d")
        for each in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str((5 - (each + 1)) * period_length + 1) + '-' + str((5 - each) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if each == 0:
                period_name = '+' + str(4 * period_length)
            periods[str(each)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (each != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop
        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.user.company_id
        user_currency = user_company.currency_id
        res_currency = self.env['res.currency'].with_context(date=date_from)
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))

        reconciliation_clause = '(l.reconciled IS FALSE)'

        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s',
                   (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        arg_list += (date_from, tuple(company_ids))

        query = '''
            SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
            FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.internal_type IN %s)
                AND ''' + reconciliation_clause + '''
                AND (l.date <= %s)
                AND l.company_id IN %s
            ORDER BY UPPER(res_partner.name)'''
        cr.execute(query, arg_list)

        partners = cr.dictfetchall()

        # put a total of 0
        for each in range(7):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], {}

        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) >= %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id IN %s'''
        cr.execute(query, (
            tuple(move_state), tuple(account_type), date_from, tuple(partner_ids), date_from, tuple(company_ids)))
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [line[0] for line in aml_ids] or []
        for line in self.env['account.move.line'].browse(aml_ids):
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = res_currency._compute(line.company_id.currency_id, user_currency, line.balance)
            if user_currency.is_zero(line_amount):
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= datetime.strptime(date_from, "%Y-%m-%d").date():
                    line_amount += res_currency._compute(partial_line.company_id.currency_id, user_currency,
                                                         partial_line.amount)
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= datetime.strptime(date_from, "%Y-%m-%d").date():
                    line_amount -= res_currency._compute(partial_line.company_id.currency_id, user_currency,
                                                         partial_line.amount)
            if not self.env.user.company_id.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 6,
                })
        history = []
        for each in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(each)]['start'] and periods[str(each)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(each)]['start'], periods[str(each)]['stop'])
            elif periods[str(each)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(each)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(each)]['stop'],)
            args_list += (date_from, tuple(company_ids))

            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s'''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [line[0] for line in aml_ids] or []
            for line in self.env['account.move.line'].browse(aml_ids).with_context(prefetch_fields=False):
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_amount = res_currency._compute(line.company_id.currency_id, user_currency, line.balance)
                if user_currency.is_zero(line_amount):
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= datetime.strptime(date_from, "%Y-%m-%d").date():
                        line_amount += res_currency._compute(partial_line.company_id.currency_id, user_currency,
                                                             partial_line.amount)
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= datetime.strptime(date_from, "%Y-%m-%d").date():
                        line_amount -= res_currency._compute(partial_line.company_id.currency_id, user_currency,
                                                             partial_line.amount)

                if not self.env.user.company_id.currency_id.is_zero(line_amount):
                    partners_amount[partner_id] += line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': each + 1,
                    })
            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt
            if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
                at_least_one_amount = True

            for each in range(5):
                during = False
                if partner['partner_id'] in history[each]:
                    during = [history[each][partner['partner_id']]]
                # Adding counter
                total[(each)] = total[(each)] + (during and during[0] or 0)
                values[str(each)] = during and during[0] or 0.0
                if not float_is_zero(values[str(each)],
                                     precision_rounding=self.env.user.company_id.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(each)] for each in range(5)])
            # Add for total
            total[(each + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
                values['name'] = browsed_partner.name and len(browsed_partner.name) >= 45 and \
                                 browsed_partner.name[0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            if at_least_one_amount or (self._context.get('include_nullified_amount') and lines[partner['partner_id']]):
                res.append(values)
        return res, total, lines

    def get_time_interval(self, date_from, period_length):
        periods = {}
        time_period = {}
        start = datetime.strptime(date_from, "%Y-%m-%d")
        for each in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str((5 - (each + 1)) * period_length + 1) + '-' + str((5 - each) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if each == 0:
                period_name = '+' + str(4 * period_length)
            periods[str(each)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (each != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop

        for each in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            time_period[str(each)] = {
                'name': (each != 0 and (
                        str((5 - (each + 1)) * period_length) + '-' + str((5 - each) * period_length)) or (
                                 '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (each != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        return time_period

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        date_from = data.get('form') and data.get('form').get('start_date')
        period_length = data.get('form') and data.get('form').get('period_length')
        target_move = data['form'].get('target_move', 'all')
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        account_type = ['payable']
        accont_moveline, total, dummy = self._get_partner_move_lines_custom(account_type, date_from, target_move,
                                                                            period_length)
        model = self.env.context.get('active_model')
        time_period = self.get_time_interval(date_from, period_length)
        data['form']['get_partner_lines'] = accont_moveline
        data['form']['get_total'] = total
        data['form']['time_period'] = time_period
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
        }
# vim:expandtab:smsartindent:tabst
