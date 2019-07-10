# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo import models, api, fields
from odoo.fields import Datetime as FieldDateTime
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountClosing(models.Model):
    """
    This object holds an interval total and a grand total of the accounts of type receivable for a company,
    as well as the last account_move that has been counted in a previous object
    It takes its earliest brother to infer from when the computation needs to be done
    in order to compute its own data.
    """
    _name = 'account.sale.closing'
    _order = 'date_closing_stop desc, sequence_number desc'
    _description = "Sale Closing"

    name = fields.Char(help="Frequency and unique sequence number", required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True)
    date_closing_stop = fields.Datetime(string="Closing Date", help='Date to which the values are computed', readonly=True, required=True)
    date_closing_start = fields.Datetime(string="Starting Date", help='Date from which the total interval is computed', readonly=True, required=True)
    frequency = fields.Selection(string='Closing Type', selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('annually', 'Annual')], readonly=True, required=True)
    total_interval = fields.Monetary(string="Period Total", help='Total in receivable accounts during the interval, excluding overlapping periods', readonly=True, required=True)
    cumulative_total = fields.Monetary(string="Cumulative Grand Total", help='Total in receivable accounts since the beginnig of times', readonly=True, required=True)
    sequence_number = fields.Integer('Sequence #', readonly=True, required=True)
    last_move_id = fields.Many2one('account.move', string='Last journal entry', help='Last Journal entry included in the grand total', readonly=True)
    last_move_hash = fields.Char(string='Last journal entry\'s inalteralbility hash', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The company's currency", readonly=True, related='company_id.currency_id', store=True)

    def _query_for_aml(self, company, first_move_sequence_number, date_start):
        params = {'company_id': company.id}
        query = '''WITH aggregate AS (SELECT m.id AS move_id,
                    aml.balance AS balance,
                    aml.id as line_id
            FROM account_move_line aml
            JOIN account_journal j ON aml.journal_id = j.id
            JOIN account_account acc ON acc.id = aml.account_id
            JOIN account_account_type t ON (t.id = acc.user_type_id AND t.type = 'receivable')
            JOIN account_move m ON m.id = aml.move_id
            WHERE j.type = 'sale'
                AND aml.company_id = %(company_id)s
                AND m.state = 'posted' '''

        if first_move_sequence_number is not False and first_move_sequence_number is not None:
            params['first_move_sequence_number'] = first_move_sequence_number
            query += '''AND m.l10n_fr_secure_sequence_number > %(first_move_sequence_number)s'''
        elif date_start:
            #the first time we compute the closing, we consider only from the installation of the module
            params['date_start'] = date_start
            query += '''AND m.date >= %(date_start)s'''

        query += " ORDER BY m.l10n_fr_secure_sequence_number DESC) "
        query += '''SELECT array_agg(move_id) AS move_ids,
                           array_agg(line_id) AS line_ids,
                           sum(balance) AS balance
                    FROM aggregate'''

        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()[0]

    def _compute_amounts(self, frequency, company):
        """
        Method used to compute all the business data of the new object.
        It will search for previous closings of the same frequency to infer the move from which
        account move lines should be fetched.
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @param {recordset} company: the company for which the closing is done
        @return {dict} containing {field: value} for each business field of the object
        """
        interval_dates = self._interval_dates(frequency, company)
        previous_closing = self.search([
            ('frequency', '=', frequency),
            ('company_id', '=', company.id)], limit=1, order='sequence_number desc')

        first_move = self.env['account.move']
        date_start = interval_dates['interval_from']
        cumulative_total = 0
        if previous_closing:
            first_move = previous_closing.last_move_id
            date_start = previous_closing.create_date
            cumulative_total += previous_closing.cumulative_total

        aml_aggregate = self._query_for_aml(company, first_move.l10n_fr_secure_sequence_number, date_start)

        total_interval = aml_aggregate['balance'] or 0
        cumulative_total += total_interval

        # We keep the reference to avoid gaps (like daily object during the weekend)
        last_move = first_move
        if aml_aggregate['move_ids']:
            last_move = last_move.browse(aml_aggregate['move_ids'][0])

        return {'total_interval': total_interval,
                'cumulative_total': cumulative_total,
                'last_move_id': last_move.id,
                'last_move_hash': last_move.l10n_fr_hash,
                'date_closing_stop': interval_dates['date_stop'],
                'date_closing_start': date_start,
                'name': interval_dates['name_interval'] + ' - ' + interval_dates['date_stop'][:10]}

    def _interval_dates(self, frequency, company):
        """
        Method used to compute the theoretical date from which account move lines should be fetched
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @param {recordset} company: the company for which the closing is done
        @return {dict} the theoretical date from which account move lines are fetched.
            date_stop date to which the move lines are fetched, always now()
            the dates are in their Odoo Database string representation
        """
        date_stop = datetime.utcnow()
        interval_from = None
        name_interval = ''
        if frequency == 'daily':
            interval_from = date_stop - timedelta(days=1)
            name_interval = _('Daily Closing')
        elif frequency == 'monthly':
            month_target = date_stop.month > 1 and date_stop.month - 1 or 12
            year_target = month_target < 12 and date_stop.year or date_stop.year - 1
            interval_from = date_stop.replace(year=year_target, month=month_target)
            name_interval = _('Monthly Closing')
        elif frequency == 'annually':
            year_target = date_stop.year - 1
            interval_from = date_stop.replace(year=year_target)
            name_interval = _('Annual Closing')

        return {'interval_from': FieldDateTime.to_string(interval_from),
                'date_stop': FieldDateTime.to_string(date_stop),
                'name_interval': name_interval}

    def write(self, vals):
        raise UserError(_('Sale Closings are not meant to be written or deleted under any circumstances.'))

    def unlink(self):
        raise UserError(_('Sale Closings are not meant to be written or deleted under any circumstances.'))

    @api.model
    def _automated_closing(self, frequency='daily'):
        """To be executed by the CRON to create an object of the given frequency for each company that needs it
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @return {recordset} all the objects created for the given frequency
        """
        res_company = self.env['res.company'].search([])
        account_closings = self.env['account.sale.closing']
        for company in res_company.filtered(lambda c: c._is_accounting_unalterable()):
            new_sequence_number = company.l10n_fr_closing_sequence_id.next_by_id()
            values = self._compute_amounts(frequency, company)
            values['frequency'] = frequency
            values['company_id'] = company.id
            values['sequence_number'] = new_sequence_number
            account_closings |= account_closings.create(values)

        return account_closings
