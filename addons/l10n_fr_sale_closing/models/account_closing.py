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

    @api.model
    def _query_get_closing(self, query, params, first_move_sequence_number, date_start):
        if first_move_sequence_number is not False and first_move_sequence_number is not None:
            query = query.replace('WHERE', 'WHERE m.l10n_fr_secure_sequence_number > %s AND')
            params = [first_move_sequence_number] + params
        elif date_start:
            #the first time we compute the closing, we consider only from the installation of the module
            query = query.replace('WHERE', 'WHERE m.date >= %s AND')
            params = [date_start] + params
        return query, params

    @api.model
    def _do_query_last_move_id(self, company, first_move_sequence_number, date_start):
        '''Select the last move_id in a separated query because we have the last move for each tax
        but we want the last move_id no matter the tax.
        :param company:                     The company owning the account.sale.closing.
        :param first_move_sequence_number:  The sequence number of the last processed move.
        :param date_start:                  The create date of the last processed move.
        :return: The last move_id as a python dictionary.
        '''
        query = '''
            SELECT
                m.id AS id,
                m.date AS date,
                m.l10n_fr_hash AS hash
            FROM account_move_line aml
                LEFT JOIN account_journal j ON aml.journal_id = j.id
                LEFT JOIN account_account acc ON acc.id = aml.account_id
                LEFT JOIN account_move m ON m.id = aml.move_id
            WHERE j.type = 'sale'
                AND aml.company_id = %s
                AND m.state = 'posted'
                AND acc.user_type_id = %s
            ORDER BY m.l10n_fr_secure_sequence_number DESC LIMIT 1
        '''
        params = [company.id, self.env.ref('account.data_account_type_revenue').id]
        self.env.cr.execute(*self._query_get_closing(query, params, first_move_sequence_number, date_start))
        res = self.env.cr.dictfetchall()
        return res and res[0] or None

    @api.model
    def _query_for_aml(self, company, first_move_sequence_number, date_start, date_end=None):
        ''' Retrieve the values for account.sale.closing records creation by
        grouping the balance of sales operations for each tax.
        Suppose an invoice with such move lines:
        | debit | credit | tax_line_id | tax_ids |
        ------------------------------------------
        |  6250 |        |             |         |
        |       |   1000 |             |       1 |
        |       |     50 |           1 |         | 5% tax applied on 1000
        |       |   2000 |             |       2 |
        |       |    200 |           2 |         | 10% tax applied on 2000
        |       |   3000 |             |         | no tax
        ------------------------------------------
        The group by result must be:
        | tax | balance |
        -----------------
        |   1 |    1000 |
        |   2 |    2000 |
        |   / |    3000 |
        -----------------
        :param company:                     The company owning the account.sale.closing.
        :param first_move_sequence_number:  The sequence number of the last processed move.
        :param date_start:                  The create date of the last processed move.
        :return: The result of the query as a python dictionaries list.
        '''
        query = '''
            SELECT
                SUM(ABS(aml.balance)) AS balance,
                tax.id,
                tax.name
            FROM account_move_line aml
                LEFT JOIN account_journal j ON aml.journal_id = j.id
                LEFT JOIN account_account acc ON acc.id = aml.account_id
                LEFT JOIN account_move m ON m.id = aml.move_id
                LEFT JOIN account_move_line_account_tax_rel taxrel ON aml.id = taxrel.account_move_line_id
                LEFT JOIN account_tax tax ON taxrel.account_tax_id = tax.id
            WHERE j.type = 'sale'
                AND aml.company_id = %s
                AND m.state = 'posted'
                AND acc.user_type_id = %s
            GROUP BY tax.id, tax.name
        '''
        params = [company.id, self.env.ref('account.data_account_type_revenue').id]

        if date_end:
            query = query.replace('WHERE', 'WHERE m.date <= %s AND')
            params = [date_end] + params
        self.env.cr.execute(*self._query_get_closing(query, params, first_move_sequence_number, date_start))
        return self.env.cr.dictfetchall()

    @api.model
    def _compute_amounts(self, frequency, company):
        """
        Method used to compute all the business data of the new object.
        It will search for previous closings of the same frequency to infer the move from which
        account move lines should be fetched.
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @param {recordset} company: the company for which the closing is done
        @return {recordset} all the objects created for the given frequency
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

        secure_seq_number = first_move.l10n_fr_secure_sequence_number

        # Fetch the last move
        last_move_vals = self._do_query_last_move_id(company, secure_seq_number, date_start)

        date_end = last_move_vals and last_move_vals['date']

        taxes_vals = self._query_for_aml(company, secure_seq_number, date_start, date_end=date_end)

        account_closings = self.env['account.sale.closing']
        for query_vals in taxes_vals:
            # Create vals for new record.
            new_sequence_number = company.l10n_fr_closing_sequence_id.next_by_id()
            name = '%s - %s - %s' % (interval_dates['name_interval'], interval_dates['date_stop'][:10], query_vals['name'])
            vals = {
                'total_interval': query_vals['balance'],
                'cumulative_total': cumulative_total + query_vals['balance'],
                'date_closing_stop': interval_dates['date_stop'],
                'date_closing_start': date_start,
                'name': name,
                'frequency': frequency,
                'company_id': company.id,
                'sequence_number': new_sequence_number,
                'last_move_id': last_move_vals['id'],
                'last_move_hash': last_move_vals['hash'],
            }
            account_closings += self.create(vals)
        return account_closings

    @api.model
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

    @api.multi
    def write(self, vals):
        raise UserError(_('Sale Closings are not meant to be written or deleted under any circumstances.'))

    @api.multi
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
            account_closings += self._compute_amounts(frequency, company)

        return account_closings
