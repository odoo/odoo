from datetime import datetime, timedelta

from openerp import models, api, fields
from openerp.fields import Datetime as FieldDateTime
from openerp.tools.translate import _
from openerp.exceptions import UserError

WRITE_MSG = _('Sale Closings are not meant to be written or deleted under any circumstances.')


class AccountClosure(models.Model):
    """
    This object holds an interval total and a grand total of the accounts of type receivable for a company,
    as well as the last account_move that has been counted in a previous object
    It takes its earliest brother to infer from when the computation needs to be done
    in order to compute its own data.
    """
    _name = 'account.sale.closure'
    _order = 'date_closure_stop desc'

    name = fields.Char(help="Frequency and unique sequence number", required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True)
    date_closure_stop = fields.Datetime(string="Closing Date", help='Date to which the values are computed', readonly=True, required=True)
    date_closure_start = fields.Datetime(string="Starting Date", help='Date from which the total interval is computed', readonly=True, required=True)
    frequency = fields.Selection(string='Closing Type', selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('annually', 'Annual')], readonly=True, required=True)
    total_interval = fields.Monetary(string="Period Total", help='Total in receivable accounts during the interval, excluding overlapping periods', readonly=True, required=True)
    total_beginning = fields.Monetary(string="Cumulative Grand Total", help='Total in receivable accounts since the beginnig of times', readonly=True, required=True)
    sequence_number = fields.Integer('Sequence #', readonly=True, required=True)
    last_move_id = fields.Many2one('account.move', string='Last journal entry', help='Last Journal entry included in the grand total', readonly=True)
    last_move_hash = fields.Char(string='Last journal entry\'s inalteralbility hash', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The company's currency", readonly=True, related='company_id.currency_id', store=True)

    def _query_for_aml(self, company, first_move_sequence_number):
        params = {'company_id': company.id}
        query = '''WITH aggregate AS 
            (SELECT m.id AS move_id,
                    aml.balance AS balance,
                    aml.id as line_id
            FROM account_move_line aml
            JOIN account_journal j ON aml.journal_id = j.id
            JOIN  (SELECT acc.id FROM account_account acc
                        JOIN account_account_type t ON t.id = acc.user_type_id
                        WHERE t.type = 'receivable') AS a
                  ON a.id = aml.account_id
            JOIN account_move m ON m.id = aml.move_id
            WHERE j.type = 'sale'
                AND aml.company_id = %(company_id)s
                AND m.state = 'posted' '''

        if first_move_sequence_number is not False and first_move_sequence_number is not None:
            params['first_move_sequence_number'] = first_move_sequence_number
            query += '''AND m.l10n_fr_secure_sequence_number > %(first_move_sequence_number)s'''

        query += "ORDER BY m.l10n_fr_secure_sequence_number DESC) "
        query += '''SELECT array(SELECT move_id FROM aggregate) AS move_ids,
                           array(SELECT line_id FROM aggregate) AS line_ids,
                           sum(balance) AS balance
                    FROM aggregate'''

        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()[0]

    def _refine_amls_for_interval(self, date, line_ids):
        query_strict_period = '''SELECT sum(balance) as balance FROM account_move_line aml
                                 JOIN account_move m ON m.id = aml.move_id
                                    WHERE aml.id IN %s
                                    AND m.date >= %s'''
        self.env.cr.execute(query_strict_period, ((tuple(line_ids), date)))
        return self.env.cr.dictfetchall()[0]

    def _compute_amounts(self, frequency, company):
        """
        Method used to compute all the business data of the new object.
        It will search for previous closures of the same frequency to infer the move from which
        account move lines should be fetched.
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @param {recordset} company: the company for which the closure is done
        @return {dict} containing {field: value} for each business field of the object
        """
        interval_dates = self._interval_dates(frequency, company)
        previous_closure = self.search([
            ('frequency', '=', frequency),
            ('company_id', '=', company.id)], limit=1, order='sequence_number desc')

        first_move = self.env['account.move']
        date_start = interval_dates['interval_from']
        if previous_closure and previous_closure.last_move_id:
            first_move = previous_closure.last_move_id
            date_start = previous_closure.create_date

        aml_aggregate = self._query_for_aml(company, first_move.l10n_fr_secure_sequence_number)

        total_beginning = total_interval = aml_aggregate['balance'] or 0

        if not first_move and aml_aggregate['line_ids']:  # It's the first time we run for this frequency
            aml_interval = self._refine_amls_for_interval(date_start, aml_aggregate['line_ids'])
            total_interval = aml_interval.get('balance')
        else:
            total_beginning += previous_closure.total_beginning

        # We keep the reference to avoid gaps (like daily object during the weekend)
        last_move = first_move
        if aml_aggregate['move_ids']:
            last_move = last_move.browse(aml_aggregate['move_ids'][0])

        return {'total_interval': total_interval,
                'total_beginning': total_beginning,
                'last_move_id': last_move.id,
                'last_move_hash': last_move.l10n_fr_hash,
                'date_closure_stop': interval_dates['date_stop'],
                'date_closure_start': date_start}

    def _interval_dates(self, frequency, company):
        """
        Method used to compute the theoretical date from which account move lines should be fetched
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @param {recordset} company: the company for which the closure is done
        @return {dict} the theoretical date from which account move lines are fetched.
            date_stop date to which the move lines are fetched, always now()
            the dates are in their Odoo Database string representation
        """
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
        """To be executed by the CRON to create an object of the given frequency for each company that needs it
        @param {string} frequency: a valid value of the selection field on the object (daily, monthly, annually)
            frequencies are literal (daily means 24 hours and so on)
        @return {recordset} all the objects created for the given frequency
        """
        def get_selection_value(field, value=''):
            for item in field.get_description(self.env)['selection']:
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
            values['sequence_number'] = new_sequence_number
            values['name'] = _('%s Closing - ') % (get_selection_value(self._fields['frequency'], value=frequency),) + values['date_closure_stop'][:10]
            account_closures |= account_closures.create(values)

        return account_closures
