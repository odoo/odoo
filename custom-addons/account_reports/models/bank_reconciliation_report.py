import logging
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class BankReconciliationReportCustomHandler(models.AbstractModel):
    _name = 'account.bank.reconciliation.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Bank Reconciliation Report Custom Handler'

    ######################
    # Options
    ######################
    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Options is needed otherwise some elements added in the post processor go on the total line
        options['ignore_totals_below_sections'] = True
        if 'active_id' in self._context and self._context.get('active_model') == 'account.journal':
            options['bank_reconciliation_report_journal_id'] = self._context['active_id']
        elif previous_options and 'bank_reconciliation_report_journal_id' in previous_options:
            options['bank_reconciliation_report_journal_id'] = previous_options['bank_reconciliation_report_journal_id']
        else:
            # This should never happen except in some test cases
            options['bank_reconciliation_report_journal_id'] = self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id

        # Remove multi-currency columns if needed
        is_multi_currency = report.user_has_groups('base.group_multi_currency') and report.user_has_groups('base.group_no_one')
        if not is_multi_currency:
            options['columns'] = [
                column for column in options['columns']
                if column['expression_label'] not in ('amount_currency', 'currency')
            ]

    ######################
    # Getter
    ######################
    def _get_bank_journal_and_currencies(self, options):
        journal = self.env['account.journal'].browse(options.get('bank_reconciliation_report_journal_id'))
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id or company_currency
        return journal, journal_currency, company_currency

    ######################
    # Return function
    ######################
    def _build_custom_engine_result(self, date=None, label=None, amount_currency=None, amount_currency_currency_id=None, currency=None, amount=0, amount_currency_id=None, has_sublines=False):
        return {
            'date': date,
            'label': label,
            'amount_currency': amount_currency,
            'amount_currency_currency_id': amount_currency_currency_id,
            'currency': currency,
            'amount': amount,
            'amount_currency_id': amount_currency_id,
            'has_sublines': has_sublines,
        }

    ######################
    # Engine
    ######################
    def _report_custom_engine_forced_currency_amount(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        _journal, journal_currency, _company_currency = self._get_bank_journal_and_currencies(options)
        return self._build_custom_engine_result(amount_currency_id=journal_currency.id)

    def _report_custom_engine_unreconciled_last_statement_receipts(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._bank_reconciliation_report_custom_engine_unreconciled_common(options, 'receipts', current_groupby, True)

    def _report_custom_engine_unreconciled_last_statement_payments(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._bank_reconciliation_report_custom_engine_unreconciled_common(options, 'payments', current_groupby, True)

    def _report_custom_engine_unreconciled_receipts(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._bank_reconciliation_report_custom_engine_unreconciled_common(options, 'receipts', current_groupby, False)

    def _report_custom_engine_unreconciled_payments(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._bank_reconciliation_report_custom_engine_unreconciled_common(options, 'payments', current_groupby, False)

    def _report_custom_engine_outstanding_receipts(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._bank_reconciliation_report_custom_engine_outstanding_common(options, 'receipts', current_groupby)

    def _report_custom_engine_outstanding_payments(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._bank_reconciliation_report_custom_engine_outstanding_common(options, 'payments', current_groupby)

    def _report_custom_engine_misc_operations(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        journal, journal_currency, _company_currency = self._get_bank_journal_and_currencies(options)

        bank_miscellaneous_domain = self._get_bank_miscellaneous_move_lines_domain(options, journal)

        misc_operations_amount = self.env["account.move.line"]._read_group(
            domain=bank_miscellaneous_domain or [],
            groupby=current_groupby or [],
            aggregates=['balance:sum']
        )[-1][0]  # Needed to get the balance from the tuples given by the read group
        return self._build_custom_engine_result(amount=misc_operations_amount or 0, amount_currency_id=journal_currency.id)

    def _report_custom_engine_last_statement_balance_amount(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        if current_groupby:
            raise UserError(_("Custom engine _report_custom_engine_last_statement_balance_amount does not support groupby"))

        journal, journal_currency, _company_currency = self._get_bank_journal_and_currencies(options)
        last_statement = self._get_last_bank_statement(journal, options)

        return self._build_custom_engine_result(amount=last_statement.balance_end_real, amount_currency_id=journal_currency.id)

    def _bank_reconciliation_report_custom_engine_unreconciled_common(self, options, internal_type, current_groupby, from_last_statement):
        """
            Retrieve unreconciled entries for bank reconciliation based on specified parameters.
            Parameters:
            - options (dict): A dictionary containing options of the report.
            - internal_type (str): The internal type used for classification (e.g., receipt, payment). For the receipt
                                   we will query the unreconciled entries with a positive amounts and for the payment
                                   the negative amounts.
            - current_groupby (str): The current grouping criteria.
            - last_statement (bool, optional): If True, query unreconciled entries from the last bank statement.
                                               Otherwise, query unreconciled entries that are not part of the last bank
                                               statement.

        """
        journal, journal_currency, _company_currency = self._get_bank_journal_and_currencies(options)
        if not journal:
            return self._build_custom_engine_result()

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def build_result_dict(query_res_lines):
            if current_groupby == 'id':
                res = query_res_lines[0]
                reconcile_rate = abs(res['suspense_balance']) / (abs(res['suspense_balance']) + abs(res['other_balance']))
                foreign_currency = self.env['res.currency'].browse(res['foreign_currency_id'])

                return self._build_custom_engine_result(
                    date=res['date'] if res['date'] else None,
                    label=res['payment_ref'] or res['ref'] or '/',
                    amount_currency=res['amount_currency'] * reconcile_rate if res['amount_currency'] else None,
                    amount_currency_currency_id=foreign_currency.id if res['foreign_currency_id'] else None,
                    currency=foreign_currency.display_name if res['foreign_currency_id'] else None,
                    amount=res['amount'] * reconcile_rate if res['amount'] else None,
                    amount_currency_id=journal_currency.id,
                )
            else:
                amount = sum(
                    res.get('amount', 0) * abs(res['suspense_balance']) / (abs(res['suspense_balance']) + abs(res['other_balance']))
                    for res in query_res_lines
                )
                return self._build_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        tables, where_clause, where_params = report._query_get(options, 'strict_range', domain=[
            ('journal_id', '=', journal.id),
            ('account_id', '!=', journal.default_account_id.id),
        ])

        if from_last_statement:
            last_statement_id = self._get_last_bank_statement(journal, options).id
            if last_statement_id:
                last_statement_id_condition = SQL("st_line.statement_id = %s", last_statement_id)
            else:
                # If there is no last statement, the last statement section must be empty and the other must have all
                # transaction
                return self._compute_result([], current_groupby, build_result_dict)
        else:
            last_statement_id_condition = SQL("st_line.statement_id IS NULL")

        # Build query
        query = SQL(
            """
           SELECT %(select_from_groupby)s,
                  st_line.id,
                  move.name,
                  move.ref,
                  move.date,
                  st_line.payment_ref,
                  st_line.amount,
                  st_line.amount_currency,
                  st_line.foreign_currency_id,
                  COALESCE(SUM(CASE WHEN account_move_line.account_id = %(suspens_journal_1)s THEN account_move_line.balance ELSE 0.0 END), 0.0) AS suspense_balance,
                  COALESCE(SUM(CASE WHEN account_move_line.account_id = %(suspens_journal_2)s THEN 0.0 ELSE account_move_line.balance END), 0.0) AS other_balance
             FROM %(tables)s
             JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
             JOIN account_move move ON move.id = st_line.move_id
            WHERE %(where_clause)s
          AND NOT st_line.is_reconciled
              AND %(is_receipt)s
              AND %(last_statement_id_condition)s
         GROUP BY %(group_by)s,
                  st_line.id,
                  move.id
            """,
            select_from_groupby=SQL("%s AS grouping_key", SQL.identifier('account_move_line', current_groupby)) if current_groupby else SQL('null'),
            suspens_journal_1=journal.suspense_account_id.id,
            suspens_journal_2=journal.suspense_account_id.id,
            tables=SQL(tables),
            where_clause=SQL(where_clause, *where_params),
            is_receipt=SQL("st_line.amount > 0") if internal_type == "receipts" else SQL("st_line.amount < 0"),
            last_statement_id_condition=last_statement_id_condition,
            group_by=SQL.identifier('account_move_line', current_groupby) if current_groupby else SQL('st_line.id'),  # Same key in the groupby because we can't put a null key in a group by
        )

        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        return self._compute_result(query_res_lines, current_groupby, build_result_dict)

    def _bank_reconciliation_report_custom_engine_outstanding_common(self, options, internal_type, current_groupby):
        """
            This engine retrieves the data of all recorded payments/receipts that have not been matched with a bank
            statement yet
        """
        journal, journal_currency, company_currency = self._get_bank_journal_and_currencies(options)
        if not journal:
            return self._build_custom_engine_result()

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def build_result_dict(query_res_lines):
            if current_groupby == 'id':
                res = query_res_lines[0]
                convert = not (journal_currency and res['currency_id'] == journal_currency.id)
                amount_currency = res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']
                balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']
                foreign_currency = self.env['res.currency'].browse(res['currency_id'])

                return self._build_custom_engine_result(
                    date=res['date'] if res['date'] else None,
                    label=res['ref'] if res['ref'] else None,
                    amount_currency=amount_currency if convert else None,
                    amount_currency_currency_id=foreign_currency.id if convert else None,
                    currency=foreign_currency.display_name if convert else None,
                    amount=company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to']) if convert else amount_currency,
                    amount_currency_id=journal_currency.id,
                )
            else:
                amount = 0
                for res in query_res_lines:
                    convert = not (journal_currency and res['currency_id'] == journal_currency.id)
                    if convert:
                        balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']
                        amount += company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to'])
                    else:
                        amount += res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']

                return self._build_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        accounts = journal._get_journal_inbound_outstanding_payment_accounts() + journal._get_journal_outbound_outstanding_payment_accounts()

        tables, where_clause, where_params = report._query_get(options, 'normal', domain=[
            ('journal_id', '=', journal.id),
            ('account_id', 'in', accounts.ids),
            ('full_reconcile_id', '=', False),
            ('amount_residual_currency', '!=', 0.0)
        ])

        # Build query
        query = SQL(
            """
           SELECT %(select_from_groupby)s,
                  account_move_line.account_id,
                  account_move_line.payment_id,
                  account_move_line.move_id,
                  account_move_line.currency_id,
                  account_move_line.move_name AS name,
                  account_move_line.ref,
                  account_move_line.date,
                  account.reconcile AS is_account_reconcile,
                  SUM(account_move_line.amount_residual) AS amount_residual,
                  SUM(account_move_line.balance) AS balance,
                  SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                  SUM(account_move_line.amount_currency) AS amount_currency
             FROM %(tables)s
             JOIN account_account account ON account.id = account_move_line.account_id
            WHERE %(where_clause)s
              AND %(is_receipt)s
         GROUP BY %(group_by)s,
                  account_move_line.account_id,
                  account_move_line.payment_id,
                  account_move_line.move_id,
                  account_move_line.currency_id,
                  account_move_line.move_name,
                  account_move_line.ref,
                  account_move_line.date,
                  account.reconcile
           """,
            select_from_groupby=SQL("%s AS grouping_key", SQL.identifier('account_move_line', current_groupby)) if current_groupby else SQL('null'),
            tables=SQL(tables),
            where_clause=SQL(where_clause, *where_params),
            is_receipt=SQL("account_move_line.balance > 0") if internal_type == "receipts" else SQL("account_move_line.balance < 0"),
            group_by=SQL.identifier('account_move_line', current_groupby) if current_groupby else SQL('account_move_line.account_id'),  # Same key in the groupby because we can't put a null key in a group by
        )
        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        return self._compute_result(query_res_lines, current_groupby, build_result_dict)

    def _compute_result(self, query_res_lines, current_groupby, build_result_dict):
        if not current_groupby:
            return build_result_dict(query_res_lines)
        else:
            rslt = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(query_res_lines)))

            return rslt

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        lines = super()._custom_line_postprocessor(report, options, lines, warnings=warnings)
        journal, journal_currency, company_currency = self._get_bank_journal_and_currencies(options)
        if not journal:
            return lines

        inconsistent_statement = self._get_inconsistent_statements(options, journal).ids
        bank_miscellaneous_domain = self._get_bank_miscellaneous_move_lines_domain(options, journal)
        has_bank_miscellaneous_move_lines = bank_miscellaneous_domain and bool(self.env['account.move.line'].search_count(bank_miscellaneous_domain, limit=1))
        last_statement, balance_gl, balance_end, unexplained_difference, general_ledger_not_matching = self._compute_journal_balances(report, options, journal, journal_currency)

        for line in lines:
            line_id = report._get_res_id_from_line_id(line['id'], 'account.report.line')
            code = self.env['account.report.line'].browse(line_id).code

            if code == "balance_bank":
                line['name'] = _("Balance of '%s'", journal.default_account_id.display_name)

            if code == "last_statement_balance":
                line['class'] = 'o_bold_tr'
                if last_statement:
                    line['columns'][1].update({
                        'name': last_statement.display_name,
                        'auditable': True,
                    })

            if code == "transaction_without_statement":
                line['class'] = 'o_bold_tr'

            if code == "misc_operations":
                line['class'] = 'o_bold_tr'

            # Check if it's a leaf node
            model, _model_id = report._get_model_info_from_id(line['id'])
            if model == "account.move.line":
                line_name = line['name'].split()
                line['name'] = line_name[0]  # This will give just the name without the ref or label

        # This part of the code will deal with the warnings displayed on top of the report
        if warnings is not None:
            if last_statement and general_ledger_not_matching:
                warnings['account_reports.journal_balance'] = {
                    'alert_type': 'warning',
                    'general_ledger_amount': balance_gl,
                    'last_bank_statement_amount': balance_end,
                    'unexplained_difference': unexplained_difference,
                }
            if inconsistent_statement:
                warnings['account_reports.inconsistent_statement_warning'] = {'alert_type': 'warning', 'args': inconsistent_statement}
            if has_bank_miscellaneous_move_lines:
                warnings['account_reports.has_bank_miscellaneous_move_lines'] = {'alert_type': 'warning', 'args': journal.default_account_id.display_name}

        return lines

    def _compute_journal_balances(self, report, options, journal, journal_currency):
        """
            This function compute all necessary information for the warning 'account_reports.journal_balance'
            :param report:          The bank reconciliation report.
            :param options:         The report options.
            :param journal:         The journal used.
        """
        # Get domain and balances
        domain = report._get_options_domain(options, 'normal')
        balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]
        last_statement, balance_end, difference, general_ledger_not_matching = self._compute_balances(options, journal, balance_gl, journal_currency)

        # Format values
        balance_gl = report.format_value(options, balance_gl, currency=journal_currency, figure_type='monetary')
        balance_end = report.format_value(options, balance_end, currency=journal_currency, figure_type='monetary')
        difference = report.format_value(options, difference, currency=journal_currency, figure_type='monetary')

        return last_statement, balance_gl, balance_end, difference, general_ledger_not_matching

    def _compute_balances(self, options, journal, balance_gl, report_currency):
        """
            This function will compute the balance of the last statement and the unexplained difference.
            :param options:         The report options.
            :param journal:         The journal used.
            :param balance_gl:      The balance of the general ledger.
            :param report_currency: The currency of the report.
        """
        report_date = fields.Date.from_string(options['date']['date_to'])
        last_statement = self._get_last_bank_statement(journal, options)
        balance_end = 0
        difference = 0
        general_ledger_not_matching = False

        if last_statement:
            lines_before_date_to = last_statement.line_ids.filtered(lambda line: line.date <= report_date)
            balance_end = last_statement.balance_start + sum(lines_before_date_to.mapped('amount'))
            difference = balance_gl - balance_end
            general_ledger_not_matching = not report_currency.is_zero(difference)

        return last_statement, balance_end, difference, general_ledger_not_matching

    def _get_last_bank_statement(self, journal, options):
        """
            Retrieve the last bank statement created using this journal.
            :param journal: The journal used.
            :param domain:  An additional domain to be applied on the account.bank.statement model.
            :return:        An account.bank.statement record or an empty recordset.
        """
        report_date = fields.Date.from_string(options['date']['date_to'])
        last_statement_domain = [('journal_id', '=', journal.id), ('statement_id', '!=', False), ('date', '<=', report_date)]
        last_st_line = self.env['account.bank.statement.line'].search(last_statement_domain, order='date desc, id desc', limit=1)
        return last_st_line.statement_id

    def _get_inconsistent_statements(self, options, journal):
        """
            Retrieve the account.bank.statements records on the range of the options date having different starting
            balance regarding its previous statement.
            :param options: The report options.
            :param journal: The account.journal from which this report has been opened.
            :return:        An account.bank.statements recordset.
        """
        return self.env['account.bank.statement'].search([
            ('journal_id', '=', journal.id),
            ('date', '<=', options['date']['date_to']),
            ('is_valid', '=', False),
        ])

    def _get_bank_miscellaneous_move_lines_domain(self, options, journal):
        """
            Get the domain to be used to retrieve the journal items affecting the bank accounts but not linked to
            a statement line. (Limited in a year)
            :param options: The report options.
            :param journal: The account.journal from which this report has been opened.
            :return:        A domain to search on the account.move.line model.

        """
        if not journal.default_account_id:
            return None

        report = self.env['account.report'].browse(options['report_id'])
        domain = [
            ('account_id', '=', journal.default_account_id.id),
            ('statement_line_id', '=', False),
            *report._get_options_domain(options, 'normal'),
        ]

        if journal.company_id.fiscalyear_lock_date:
            domain.append(('date', '>', journal.company_id.fiscalyear_lock_date))

        if journal.company_id.account_opening_move_id:
            domain.append(('move_id', '!=', journal.company_id.account_opening_move_id.id))

        return domain

    ################
    # Audit
    ################
    def action_audit_cell(self, options, params):
        report_line = self.env['account.report.line'].browse(params['report_line_id'])
        if report_line.code == "balance_bank":
            return self.action_redirect_to_general_ledger(options)
        elif report_line.code == "misc_operations":
            return self.open_bank_miscellaneous_move_lines(options)
        elif report_line.code == "last_statement_balance":
            return self.action_redirect_to_bank_statement_widget(options)
        else:
            return report_line.report_id.action_audit_cell(options, params)

    ################
    # ACTIONS
    ################
    def action_redirect_to_general_ledger(self, options):
        """
            Action to redirect to the general ledger
            :param options:     The report options.
            :return:            Actions to the report
        """
        general_ledger_action = self.env['ir.actions.actions']._for_xml_id('account_reports.action_account_report_general_ledger')
        general_ledger_action['params'] = {
            'options': options,
            'ignore_session': True,
        }

        return general_ledger_action

    def action_redirect_to_bank_statement_widget(self, options):
        """
            Redirect the user to the requested bank statement, if empty displays all bank transactions of the journal.
            :param options:     The report options.
            :param params:      The action params containing at least 'statement_id', can be false.
            :return:            A dictionary representing an ir.actions.act_window.
        """
        journal = self.env['account.journal'].browse(options.get('bank_reconciliation_report_journal_id'))
        last_statement = self._get_last_bank_statement(journal, options)
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={'create': False, 'search_default_statement_id': last_statement.id},
            name=last_statement.display_name,
        )

    def open_bank_miscellaneous_move_lines(self, options):
        """
            An action opening the account.move.line tree view affecting the bank account balance but not linked to
            a bank statement line.
            :param options: The report options.
            :param params:  -Not used-.
            :return:        An action redirecting to the tree view of journal items.
        """
        journal = self.env['account.journal'].browse(options['bank_reconciliation_report_journal_id'])

        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'list',
            'view_mode': 'list',
            'target': 'current',
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'domain': self.env['account.bank.reconciliation.report.handler']._get_bank_miscellaneous_move_lines_domain(options, journal),
        }

    def bank_reconciliation_report_open_inconsistent_statements(self, options, params=None):
        """
            An action opening the account.bank.statement view (form or list) depending the 'inconsistent_statement_ids'
            key set on the options.
            :param options: The report options.
            :param params:  -Not used-.
            :return:        An action redirecting to a view of statements.
        """
        inconsistent_statement_ids = params['args']
        action = {
            'name': _("Inconsistent Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
        }
        if len(inconsistent_statement_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': inconsistent_statement_ids[0],
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'list',
                'domain': [('id', 'in', inconsistent_statement_ids)],
                'views': [(False, 'list')],
            })
        return action
