# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import float_is_zero, SQL
from odoo.exceptions import UserError

from itertools import chain


class MulticurrencyRevaluationReportCustomHandler(models.AbstractModel):
    """Manage Unrealized Gains/Losses.

    In multi-currencies environments, we need a way to control the risk related
    to currencies (in case some are higthly fluctuating) and, in some countries,
    some laws also require to create journal entries to record the provisionning
    of a probable future expense related to currencies. Hence, people need to
    create a journal entry at the beginning of a period, to make visible the
    probable expense in reports (and revert it at the end of the period, to
    recon the real gain/loss.
    """
    _name = 'account.multicurrency.revaluation.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Multicurrency Revaluation Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'components': {
                'AccountReportFilters': 'account_reports.MulticurrencyRevaluationReportFilters',
            },
            'templates': {
                'AccountReportLineName': 'account_reports.MulticurrencyRevaluationReportLineName',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        active_currencies = self.env['res.currency'].search([('active', '=', True)])
        if len(active_currencies) < 2:
            raise UserError(_("You need to activate more than one currency to access this report."))
        rates = active_currencies._get_rates(self.env.company, options.get('date').get('date_to'))
        # Normalize the rates to the company's currency
        company_rate = rates[self.env.company.currency_id.id]
        for key in rates.keys():
            rates[key] /= company_rate

        options['currency_rates'] = {
            str(currency_id.id): {
                'currency_id': currency_id.id,
                'currency_name': currency_id.name,
                'currency_main': self.env.company.currency_id.name,
                'rate': (rates[currency_id.id]
                         if not previous_options.get('currency_rates', {}).get(str(currency_id.id), {}).get('rate') else
                         float(previous_options['currency_rates'][str(currency_id.id)]['rate'])),
            } for currency_id in active_currencies
        }

        for currency_rates in options['currency_rates'].values():
            if currency_rates['rate'] == 0:
                raise UserError(_("The currency rate cannot be equal to zero"))

        options['company_currency'] = options['currency_rates'].pop(str(self.env.company.currency_id.id))
        options['custom_rate'] = any(
            not float_is_zero(cr['rate'] - rates[cr['currency_id']], 20)
            for cr in options['currency_rates'].values()
        )

        options['multi_currency'] = True
        options['buttons'].append({'name': _('Adjustment Entry'), 'sequence': 30, 'action': 'action_multi_currency_revaluation_open_revaluation_wizard', 'always_show': True})

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        if len(self.env.companies) > 1:
            warnings['account_reports.multi_currency_revaluation_report_warning_multicompany'] = {'alert_type': 'warning'}
        if options['custom_rate']:
            warnings['account_reports.multi_currency_revaluation_report_warning_custom_rate'] = {'alert_type': 'warning'}

    def _custom_line_postprocessor(self, report, options, lines):
        line_to_adjust_id = self.env.ref('account_reports.multicurrency_revaluation_to_adjust').id
        line_excluded_id = self.env.ref('account_reports.multicurrency_revaluation_excluded').id

        rslt = []
        for index, line in enumerate(lines):
            res_model_name, res_id = report._get_model_info_from_id(line['id'])

            if res_model_name == 'account.report.line' and (
                   (res_id == line_to_adjust_id and report._get_model_info_from_id(lines[index + 1]['id']) == ('account.report.line', line_excluded_id)) or
                   (res_id == line_excluded_id and index == len(lines) - 1)
            ):
                # 'To Adjust' and 'Excluded' lines need to be hidden if they have no child
                continue

            elif res_model_name == 'res.currency':
                # Include the rate in the currency_id group lines
                line['name'] = '{for_cur} (1 {comp_cur} = {rate:.6} {for_cur})'.format(
                    for_cur=line['name'],
                    comp_cur=self.env.company.currency_id.display_name,
                    rate=float(options['currency_rates'][str(res_id)]['rate']),
                )

            elif res_model_name == 'account.account':
                # Mark the included/excluded lines, so that the custom component templates knows what label to put on them
                line['is_included_line'] = report._get_res_id_from_line_id(line['id'], 'account.account') == line_to_adjust_id

            # Inject the related model into the line dict in order to use it on the custom component template on js side to display buttons
            line['cur_revaluation_line_model'] = res_model_name

            rslt.append(line)

        return rslt

    def _custom_groupby_line_completer(self, report, options, line_dict):
        model_info_from_id = report._get_model_info_from_id(line_dict['id'])
        if model_info_from_id[0] == 'res.currency':
            line_dict['unfolded'] = True
            line_dict['unfoldable'] = False

    def action_multi_currency_revaluation_open_revaluation_wizard(self, options):
        """Open the revaluation wizard."""
        form = self.env.ref('account_reports.view_account_multicurrency_revaluation_wizard', False)
        return {
            'name': _("Make Adjustment Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.multicurrency.revaluation.wizard',
            'view_mode': 'form',
            'view_id': form.id,
            'views': [(form.id, 'form')],
            'multi': 'True',
            'target': 'new',
            'context': {
                **self._context,
                'multicurrency_revaluation_report_options': options,
            },
        }

    # ACTIONS
    def action_multi_currency_revaluation_open_general_ledger(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        account_id = report._get_res_id_from_line_id(params['line_id'], 'account.account')
        account_line_id = report._get_generic_line_id('account.account', account_id)
        general_ledger_options = self.env.ref('account_reports.general_ledger_report').get_options(options)
        general_ledger_options['unfolded_lines'] = [account_line_id]

        general_ledger_action = self.env['ir.actions.actions']._for_xml_id('account_reports.action_account_report_general_ledger')
        general_ledger_action['params'] = {
            'options': general_ledger_options,
            'ignore_session': True,
        }

        return general_ledger_action

    def action_multi_currency_revaluation_toggle_provision(self, options, params):
        """ Include/exclude an account from the provision. """
        res_ids_map = self.env['account.report']._get_res_ids_from_line_id(params['line_id'], ['res.currency', 'account.account'])
        account = self.env['account.account'].browse(res_ids_map['account.account'])
        currency = self.env['res.currency'].browse(res_ids_map['res.currency'])
        if currency in account.exclude_provision_currency_ids:
            account.exclude_provision_currency_ids -= currency
        else:
            account.exclude_provision_currency_ids += currency
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_multi_currency_revaluation_open_currency_rates(self, options, params=None):
        """ Open the currency rate list. """
        currency_id = self.env['account.report']._get_res_id_from_line_id(params['line_id'], 'res.currency')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Currency Rates (%s)', self.env['res.currency'].browse(currency_id).display_name),
            'views': [(False, 'list')],
            'res_model': 'res.currency.rate',
            'context': {**self.env.context, **{'default_currency_id': currency_id, 'active_id': currency_id}},
            'domain': [('currency_id', '=', currency_id)],
        }

    def _report_custom_engine_multi_currency_revaluation_to_adjust(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._multi_currency_revaluation_get_custom_lines(options, 'to_adjust', current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_multi_currency_revaluation_excluded(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._multi_currency_revaluation_get_custom_lines(options, 'excluded', current_groupby, next_groupby, offset=offset, limit=limit)

    def _multi_currency_revaluation_get_custom_lines(self, options, line_code, current_groupby, next_groupby, offset=0, limit=None):
        def build_result_dict(report, query_res):
            return {
                'balance_currency': query_res['balance_currency'] if len(query_res['currency_id']) == 1 else None,
                'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                'balance_operation': query_res['balance_operation'],
                'balance_current': query_res['balance_current'],
                'adjustment': query_res['adjustment'],
                'has_sublines': query_res['aml_count'] > 0,
            }

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        # No need to run any SQL if we're computing the main line: it does not display any total
        if not current_groupby:
            return {
                'balance_currency': None,
                'currency_id': None,
                'balance_operation': None,
                'balance_current': None,
                'adjustment': None,
                'has_sublines': False,
            }

        query = "(VALUES {})".format(', '.join("(%s, %s)" for rate in options['currency_rates']))
        params = list(chain.from_iterable((cur['currency_id'], cur['rate']) for cur in options['currency_rates'].values()))
        custom_currency_table_query = SQL(query, *params)
        date_to = options['date']['date_to']
        select_part_not_an_exchange_move_id = SQL(
            """
            NOT EXISTS (
                SELECT 1
                  FROM account_partial_reconcile part_exch
                 WHERE part_exch.exchange_move_id = account_move_line.move_id
                   AND part_exch.max_date <= %s
            )
            """,
            date_to
        )

        query = report._get_report_query(options, 'strict_range')
        groupby_field_sql = self.env['account.move.line']._field_to_sql("account_move_line", current_groupby, query)
        tail_query = report._get_engine_query_tail(offset, limit)
        full_query = SQL(
            """
            WITH custom_currency_table(currency_id, rate) AS (%(custom_currency_table_query)s)

            -- Final select that gets the following lines:
            -- (where there is a change in the rates of currency between the creation of the move and the full payments)
            -- - Moves that don't have a payment yet at a certain date
            -- - Moves that have a partial but are not fully paid at a certain date
            SELECT
                   subquery.grouping_key,
                   ARRAY_AGG(DISTINCT(subquery.currency_id)) AS currency_id,
                   SUM(subquery.balance_currency) AS balance_currency,
                   SUM(subquery.balance_operation) AS balance_operation,
                   SUM(subquery.balance_current) AS balance_current,
                   SUM(subquery.adjustment) AS adjustment,
                   COUNT(subquery.aml_id) AS aml_count
              FROM (
                -- Get moves that have at least one partial at a certain date and are not fully paid at that date
                SELECT
                       %(groupby_field_sql)s AS grouping_key,
                       ROUND(account_move_line.balance - SUM(ara.amount_debit) + SUM(ara.amount_credit), aml_comp_currency.decimal_places) AS balance_operation,
                       ROUND(account_move_line.amount_currency - SUM(ara.amount_debit_currency) + SUM(ara.amount_credit_currency), aml_currency.decimal_places) AS balance_currency,
                       ROUND(account_move_line.amount_currency - SUM(ara.amount_debit_currency) + SUM(ara.amount_credit_currency), aml_currency.decimal_places) / custom_currency_table.rate AS balance_current,
                       (
                          -- adjustment is computed as: balance_current - balance_operation
                          ROUND( account_move_line.amount_currency - SUM(ara.amount_debit_currency) + SUM(ara.amount_credit_currency), aml_currency.decimal_places) / custom_currency_table.rate
                          - ROUND(account_move_line.balance - SUM(ara.amount_debit) + SUM(ara.amount_credit), aml_comp_currency.decimal_places)
                       ) AS adjustment,
                       account_move_line.currency_id AS currency_id,
                       account_move_line.id AS aml_id
                  FROM %(table_references)s,
                       account_account AS account,
                       res_currency AS aml_currency,
                       res_currency AS aml_comp_currency,
                       custom_currency_table,

                       -- Get for each move line the amount residual and amount_residual currency
                       -- both for matched "debit" and matched "credit" the same way as account.move.line
                       -- '_compute_amount_residual()' method does
                       -- (using LATERAL greatly reduce the number of lines for which we have to compute it)
                       LATERAL (
                               -- Get sum of matched "debit" amount and amount in currency for related move line at date
                               SELECT COALESCE(SUM(part.amount), 0.0) AS amount_debit,
                                      ROUND(
                                          SUM(part.debit_amount_currency),
                                          curr.decimal_places
                                      ) AS amount_debit_currency,
                                      0.0 AS amount_credit,
                                      0.0 AS amount_credit_currency,
                                      account_move_line.currency_id AS currency_id,
                                      account_move_line.id AS aml_id
                                 FROM account_partial_reconcile part
                                 JOIN res_currency curr ON curr.id = part.debit_currency_id
                                WHERE account_move_line.id = part.debit_move_id
                                  AND part.max_date <= %(date_to)s
                             GROUP BY aml_id,
                                      curr.decimal_places
                           UNION
                               -- Get sum of matched "credit" amount and amount in currency for related move line at date
                               SELECT 0.0 AS amount_debit,
                                      0.0 AS amount_debit_currency,
                                      COALESCE(SUM(part.amount), 0.0) AS amount_credit,
                                      ROUND(
                                          SUM(part.credit_amount_currency),
                                          curr.decimal_places
                                      ) AS amount_credit_currency,
                                      account_move_line.currency_id AS currency_id,
                                      account_move_line.id AS aml_id
                                 FROM account_partial_reconcile part
                                 JOIN res_currency curr ON curr.id = part.credit_currency_id
                                WHERE account_move_line.id = part.credit_move_id
                                  AND part.max_date <= %(date_to)s
                             GROUP BY aml_id,
                                      curr.decimal_places
                            ) AS ara
                 WHERE %(search_condition)s
                   AND account_move_line.account_id = account.id
                   AND account_move_line.currency_id = aml_currency.id
                   AND account_move_line.company_currency_id = aml_comp_currency.id
                   AND account_move_line.currency_id = custom_currency_table.currency_id
                   AND account.account_type NOT IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance')
                   AND (
                        account.currency_id != account_move_line.company_currency_id
                        OR (
                            account.account_type IN ('asset_receivable', 'liability_payable')
                            AND (account_move_line.currency_id != account_move_line.company_currency_id)
                        )
                   )
                   AND %(exist_condition)s (
                        SELECT 1
                          FROM account_account_exclude_res_currency_provision
                         WHERE account_account_id = account_move_line.account_id
                           AND res_currency_id = account_move_line.currency_id
                   )
                   AND (%(select_part_not_an_exchange_move_id)s)
              GROUP BY account_move_line.id, grouping_key, aml_comp_currency.decimal_places,  aml_currency.decimal_places, custom_currency_table.rate
                HAVING ROUND(account_move_line.balance - SUM(ara.amount_debit) + SUM(ara.amount_credit), aml_comp_currency.decimal_places) != 0
                    OR ROUND(account_move_line.amount_currency - SUM(ara.amount_debit_currency) + SUM(ara.amount_credit_currency), aml_currency.decimal_places) != 0.0

                UNION
                -- Moves that don't have a payment yet at a certain date
                SELECT
                       %(groupby_field_sql)s AS grouping_key,
                       account_move_line.balance AS balance_operation,
                       account_move_line.amount_currency AS balance_currency,
                       account_move_line.amount_currency / custom_currency_table.rate AS balance_current,
                       account_move_line.amount_currency / custom_currency_table.rate - account_move_line.balance AS adjustment,
                       account_move_line.currency_id AS currency_id,
                       account_move_line.id AS aml_id
                  FROM %(table_references)s
                  JOIN account_account account ON account_move_line.account_id = account.id
                  JOIN custom_currency_table ON custom_currency_table.currency_id = account_move_line.currency_id
                 WHERE %(search_condition)s
                   AND account.account_type NOT IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance')
                   AND (
                        account.currency_id != account_move_line.company_currency_id
                        OR (
                            account.account_type IN ('asset_receivable', 'liability_payable')
                            AND (account_move_line.currency_id != account_move_line.company_currency_id)
                        )
                   )
                   AND %(exist_condition)s (
                        SELECT 1
                          FROM account_account_exclude_res_currency_provision
                         WHERE account_account_id = account_id
                           AND res_currency_id = account_move_line.currency_id
                   )
                   AND (%(select_part_not_an_exchange_move_id)s)
                   AND NOT EXISTS (
                        SELECT 1 FROM account_partial_reconcile part
                        WHERE (part.debit_move_id = account_move_line.id OR part.credit_move_id = account_move_line.id)
                          AND part.max_date <= %(date_to)s
                   )
                   AND (account_move_line.balance != 0.0 OR account_move_line.amount_currency != 0.0)

            ) subquery

            GROUP BY grouping_key
            ORDER BY grouping_key
            %(tail_query)s
            """,
            groupby_field_sql=groupby_field_sql,
            custom_currency_table_query=custom_currency_table_query,
            exist_condition=SQL('NOT EXISTS') if line_code == 'to_adjust' else SQL('EXISTS'),
            table_references=query.from_clause,
            date_to=date_to,
            tail_query=tail_query,
            search_condition=query.where_clause,
            select_part_not_an_exchange_move_id=select_part_not_an_exchange_move_id,
        )
        self._cr.execute(full_query)
        query_res_lines = self._cr.dictfetchall()

        if not current_groupby:
            return build_result_dict(report, query_res_lines and query_res_lines[0] or {})
        else:
            rslt = []
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                rslt.append((grouping_key, build_result_dict(report, query_res)))
            return rslt
