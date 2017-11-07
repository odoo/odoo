from datetime import datetime, timedelta
import calendar

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

WRITE_MSG = _('Closures of receivable accounts are not meant to be written or deleted under any circumstances.')


class AccountClosure(models.Model):
    _name = 'account.sale.closure'

    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_closure_stop = fields.Datetime(string="Closing Date", help='Date to which the values are computed', readonly=True)
    date_closure_start = fields.Datetime(string="Starting Date", help='Date from which the total interval is computed', readonly=True)
    frequency = fields.Selection(string='Interval of the closure', selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('annually', 'Annually')], readonly=True)
    total_interval = fields.Monetary(string="Period Total", help='Total in receivable accounts during the interval', readonly=True)
    total_fiscal = fields.Monetary(string="Fiscal Year Cumulative Total", help='Total in receivable accounts since the beginning of the fiscal year', readonly=True)
    total_beginning = fields.Monetary(string="Cumulative Grand Total", help='Total in receivable accounts since the beginning of times', readonly=True)
    sequence_number = fields.Integer('Sequence number', readonly=True)
    move_ids = fields.Many2many('account.move', string='Journal entries that are included in the computation', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The company's currency", readonly=True)

    def _build_query(self, company, date_start='', date_stop='', avoid_move_ids=[]):
        params = {'company_id': company.id}
        query = '''SELECT m.write_date AS move_write_date, m.id AS move_id, debit-credit AS balance
            FROM account_move_line aml
            JOIN account_journal j ON aml.journal_id = j.id
            JOIN  (SELECT acc.id FROM account_account acc
                        JOIN account_account_type t ON t.id = acc.user_type_id
                        WHERE t.type = 'receivable') AS a
                  ON a.id = aml.account_id
            JOIN account_move m ON m.id = aml.move_id
            WHERE j.type = 'sale'
                AND aml.company_id = %(company_id)s
                AND m.state = 'posted'
                AND m.write_date '''

        if date_start and date_stop:
            params['date_stop'] = date_stop
            params['date_start'] = date_start
            query += 'BETWEEN %(date_start)s AND %(date_stop)s'
        elif not date_start:
            params['date_stop'] = date_stop
            query += '<= %(date_stop)s'

        if avoid_move_ids:
            params['avoid_move_ids'] = tuple(avoid_move_ids)
            query += 'AND m.id NOT IN %(avoid_move_ids)s'

        return query, params

    def _compute_amounts(self, frequency, company):
        interval_dates = self._interval_dates(frequency, company)
        previous_closure = self.search([
            ('frequency', '=', frequency),
            ('company_id', '=', company.id)], limit=1, order='sequence_number desc')

        date_query_start = ''
        previous_move_ids = []
        riding_fiscal_periods = interval_dates['riding_fiscal_periods']

        if previous_closure and previous_closure.move_ids:
            previous_date = previous_closure.move_ids.sorted(key=lambda m: m.write_date)[-1].write_date
            date_query_start = min(previous_date, interval_dates['interval_from'])
            previous_move_ids = previous_closure.move_ids.ids
            riding_fiscal_periods = date_query_start < interval_dates['fiscal_from']

        query, params = self._build_query(company, date_query_start, interval_dates['date_stop'])
        self.env.cr.execute(query, params)
        results = self.env.cr.dictfetchall()

        date_interval_start = date_query_start and date_query_start or interval_dates['interval_from']
        aml_interval = filter(lambda aml: aml['move_write_date'] >= date_interval_start, results)
        aml_beginning = filter(lambda aml: aml['move_id'] not in previous_move_ids, results)

        total_interval = sum(aml['balance'] for aml in aml_interval)
        total_beginning = sum(aml['balance'] for aml in aml_beginning)

        aml_fiscal = []
        total_fiscal = 0
        if riding_fiscal_periods:
            aml_fiscal = filter(lambda aml: aml['move_write_date'] >= interval_dates['fiscal_from'], results)
            total_fiscal = sum(aml['balance'] for aml in aml_fiscal)
        else:
            aml_fiscal = filter(lambda aml: aml['move_id'] not in previous_move_ids, results)
            total_fiscal = previous_closure.total_fiscal + sum(aml['balance'] for aml in aml_fiscal)

        return {'total_interval': total_interval,
                'total_fiscal': total_fiscal,
                'total_beginning': previous_closure.total_beginning + total_beginning,
                'move_ids': [(4, aml['move_id'], False) for aml in aml_interval],
                'date_closure_stop': interval_dates['date_stop'],
                'date_closure_start': interval_dates['interval_from']}

    def _interval_dates(self, frequency, company):
        def time_to_string(datetime):
            return datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        date_stop = datetime.utcnow()
        fiscal_year_dates = company.compute_fiscalyear_dates(datetime(year=date_stop.year, month=date_stop.month, day=date_stop.day))
        interval_from = None
        if frequency == 'daily':
            interval_from = date_stop - timedelta(days=1)
        elif frequency == 'monthly':
            month_target = date_stop.month > 1 and date_stop.month - 1 or 12
            year_target = month_target < 12 and date_stop.year or date_stop.year - 1
            interval_from = date_stop.replace(year=year_target, month=month_target)
        elif frequency == 'annually':
            year_target = date_stop.year - 1
            interval_from = date_stop.replace(year=year_target)

        return {'interval_from': time_to_string(interval_from),
                'fiscal_from': time_to_string(fiscal_year_dates['date_from']),
                'date_stop': time_to_string(date_stop),
                'riding_fiscal_periods': interval_from < fiscal_year_dates['date_from']}

    @api.multi
    def write(self, vals):
        raise UserError(WRITE_MSG)

    @api.multi
    def unlink(self):
        raise UserError(WRITE_MSG)

    @api.model
    def automated_closure(self, frequency='daily'):
        # To be executed by the CRON to compute all the amount
        # call every _compute to get the amounts
        res_company = self.env['res.company'].search([])
        account_closures = self.env['account.sale.closure']
        for company in res_company.filtered(lambda c: c._is_accounting_unalterable()):
            new_sequence_number = company.l10n_fr_closure_sequence_id.next_by_id()
            values = self._compute_amounts(frequency, company)
            values['frequency'] = frequency
            values['company_id'] = company.id
            values['currency_id'] = company.currency_id.id
            values['sequence_number'] = new_sequence_number
            account_closures |= account_closures.create(values)

        return account_closures

    def do_all_frequencies(self):
        results = self.env['account.sale.closure']
        for frequency in [freq[0] for freq in self._fields['frequency'].selection]:
            results |= self.automated_closure(frequency)
        return results
