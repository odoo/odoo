from datetime import datetime, timedelta

from openerp import models, api, fields
from openerp.fields import Datetime as FieldDateTime
from openerp.tools.translate import _
from openerp.exceptions import UserError

WRITE_MSG = _('Sale Closings are not meant to be written or deleted under any circumstances.')


class AccountClosure(models.Model):
    _name = 'account.sale.closure'

    name = fields.Char(help="Frequency and unique sequence number")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_closure_stop = fields.Datetime(string="Closing Date", help='Date to which the values are computed', readonly=True)
    date_closure_start = fields.Datetime(string="Starting Date", help='Date from which the total interval is computed', readonly=True)
    frequency = fields.Selection(string='Closing Type', selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('annually', 'Annual')], readonly=True)
    total_interval = fields.Monetary(string="Period Total", help='Total in receivable accounts during the interval, excluding overlapping periods', readonly=True)
    total_beginning = fields.Monetary(string="Cumulative Grand Total", help='Total in receivable accounts since the beginning of times', readonly=True)
    sequence_number = fields.Integer('Sequence #', readonly=True)
    move_ids = fields.Many2many('account.move', string='Journal entries that are included in the computation', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The company's currency", readonly=True)

    def _query_closures_for_move_ids(self, frequency, company):
        query = '''SELECT rel.account_move_id as move_id
                    FROM account_move_account_sale_closure_rel rel
                    JOIN account_sale_closure clo on rel.account_sale_closure_id = clo.id
                    JOIN account_move m on rel.account_move_id = m.id
                    WHERE clo.frequency = %(frequency)s
                        AND clo.company_id = %(company_id)s
                        AND m.company_id = %(company_id)s
                        AND m.state = 'posted' '''

        self.env.cr.execute(query, {'frequency': frequency, 'company_id': company.id})
        return [res['move_id'] for res in self.env.cr.dictfetchall()]

    def _build_query_for_aml(self, company, date_start='', date_stop='', avoid_move_ids=[]):
        params = {'company_id': company.id}
        query = '''SELECT m.write_date AS move_write_date,
                          m.id AS move_id,
                          debit-credit AS balance
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

    def _query_for_aml(self, company, date_start='', date_stop='', avoid_move_ids=[]):
        query, params = self._build_query_for_aml(company, date_start, date_stop, avoid_move_ids)
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _compute_amounts(self, frequency, company):
        interval_dates = self._interval_dates(frequency, company)
        previous_closure = self.search([
            ('frequency', '=', frequency),
            ('company_id', '=', company.id)], limit=1, order='sequence_number desc')

        date_query_start = ''
        if previous_closure and previous_closure.move_ids:
            previous_date = previous_closure.move_ids.sorted(key=lambda m: m.write_date)[-1].write_date
            date_query_start = min(previous_date, interval_dates['interval_from'])

        moves_already_counted = self._query_closures_for_move_ids(frequency, company)
        aml_fetched = self._query_for_aml(company, date_query_start, interval_dates['date_stop'], moves_already_counted)

        date_interval_start = date_query_start and date_query_start or interval_dates['interval_from']
        aml_interval = filter(lambda aml: aml['move_write_date'] >= date_interval_start, aml_fetched)

        total_interval = sum(aml['balance'] for aml in aml_interval)
        total_beginning = sum(aml['balance'] for aml in aml_fetched)

        return {'total_interval': total_interval,
                'total_beginning': previous_closure.total_beginning + total_beginning,
                'move_ids': [(4, aml['move_id'], False) for aml in aml_interval],
                'date_closure_stop': interval_dates['date_stop'],
                'date_closure_start': interval_dates['interval_from']}

    def _interval_dates(self, frequency, company):
        date_stop = datetime.utcnow()
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

        return {'interval_from': FieldDateTime.to_string(interval_from),
                'date_stop': FieldDateTime.to_string(date_stop)}

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
        def get_selection_value(field, value=''):
            for item in field.selection:
                if item[0] == value:
                    return item[1]
            return value

        res_company = self.env['res.company'].search([])
        account_closures = self.env['account.sale.closure']
        for company in res_company.filtered(lambda c: c._is_accounting_unalterable()):
            new_sequence_number = company.l10n_fr_closure_sequence_id.next_by_id()
            values = self._compute_amounts(frequency, company)
            values['frequency'] = frequency
            values['company_id'] = company.id
            values['currency_id'] = company.currency_id.id
            values['sequence_number'] = new_sequence_number
            values['name'] = _('%s Closing - ') % (get_selection_value(self._fields['frequency'], value=frequency),) + values['date_closure_stop'][:10]
            account_closures |= account_closures.create(values)

        return account_closures

    def do_all_frequencies(self):
        results = self.env['account.sale.closure']
        for frequency in [freq[0] for freq in self._fields['frequency'].selection]:
            results |= self.automated_closure(frequency)
        return results
