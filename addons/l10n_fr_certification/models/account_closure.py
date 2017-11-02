from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError
from datetime import datetime, timedelta, date
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

WRITE_MSG = _('Closures of receivable accounts are not meant to be written or deleted under any circumstances.')

class AccountClosure(models.Model):
    _name = 'account.sale.closure'

    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_closure_stop = fields.Datetime('Date to which the values are computed', readonly=True)
    date_closure_start = fields.Datetime('Date from which the total interval is computed', readonly=True)
    frequency = fields.Selection(string='Interval of the closure', selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('annually', 'Annually')], readonly=True)
    total_interval = fields.Monetary('Total in receivable accounts during the interval', readonly=True)
    total_fiscal = fields.Monetary('Total in receivable accounts since the beginning of the fiscal year', readonly=True)
    total_beginning = fields.Monetary('Total in receivable accounts since the beginning of times', readonly=True)
    sequence_number = fields.Integer('Sequence number', readonly=True)
    move_ids = fields.Many2many('account.move', string='Journal entries that are included in the computation', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency of the computation', help="The company's currency", readonly=True)

    def _build_query(self, company, date_start='', date_stop='', avoid_move_ids=[]):
        params = {'company_id': company.id}
        query = '''SELECT m.write_date AS move_write_date, m.id AS move_id, debit-credit AS balance FROM account_move_line aml
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

        if previous_closure and previous_closure.move_ids:
            date_interval_start = previous_closure.move_ids.sorted(key=lambda m: m.write_date)[-1].write_date
            previous_move_ids = previous_closure.move_ids
            rinding_fiscal_periods = previous_closure.create_date < interval_dates['fiscal_from']

            query, params = self._build_query(company, date_interval_start, interval_dates['date_stop'])
            self.env.cr.execute(query, params)
            results = self.env.cr.dictfetchall()

            aml_interval = filter(lambda aml: aml['move_write_date'] >= date_interval_start, results)
            aml_fiscal = filter(lambda aml: aml['move_write_date'] >= interval_dates['fiscal_from'] and aml['move_id'] not in previous_move_ids, results)
            aml_beginning = filter(lambda aml: aml['move_id'] not in previous_move_ids, results)

            total_interval = sum(aml['balance'] for aml in aml_interval)
            total_fiscal = sum(aml['balance'] for aml in aml_fiscal)
            total_beginning = sum(aml['balance'] for aml in aml_beginning)

            return {'total_interval': total_interval,
                    'total_fiscal': total_fiscal + (not rinding_fiscal_periods and previous_closure.total_fiscal or 0),
                    'total_beginning': previous_closure.total_beginning + total_beginning,
                    'move_ids': [(4, aml['move_id'], False) for aml in aml_interval],
                    'date_closure_stop': interval_dates['date_stop'],
                    'date_closure_start': interval_dates['interval_from']}
        else:
            query_full, params_full = self._build_query(company, date_stop=interval_dates['date_stop'])
            self.env.cr.execute(query_full, params_full)
            results_full = self.env.cr.dictfetchall()

            total_beginning = sum(aml['balance'] for aml in results_full)
            total_fiscal = sum(aml['balance'] for aml in filter(lambda aml: aml['move_write_date'] >= interval_dates['fiscal_from'], results_full))
            total_interval = sum(aml['balance'] for aml in filter(lambda aml: aml['move_write_date'] >= interval_dates['interval_from'], results_full))

            return {'total_interval': total_interval,
                    'total_fiscal': total_fiscal,
                    'total_beginning': total_beginning,
                    'move_ids': [(4, aml['move_id'], False) for aml in results_full],
                    'date_closure_stop': interval_dates['date_stop'],
                    'date_closure_start': interval_dates['interval_from']}

    def _interval_dates(self, frequency, company):
        def time_to_string(datetime):
            return datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        date_stop = datetime.utcnow()
        fiscal_year_dates = company.compute_fiscalyear_dates(date_stop)
        delta_time = None
        if frequency == 'daily':
            delta_time = timedelta(days=1)
        elif frequency == 'monthly':
            delta_time = timedelta(days=30)
        elif frequency == 'annually':
            delta_time = timedelta(days=365)

        interval_from = date_stop - delta_time

        return {'interval_from': time_to_string(interval_from),
                'fiscal_from': time_to_string(fiscal_year_dates['date_from']),
                'date_stop': time_to_string(date_stop)}

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
