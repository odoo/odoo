# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import models, fields, api, osv
from odoo.addons.web.controllers.utils import clean_action
from odoo.tools import SQL, Query


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_analytic_groupby = fields.Boolean(
        string="Analytic Group By",
        compute=lambda x: x._compute_report_option_filter('filter_analytic_groupby'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )

    def _get_options_initializers_forced_sequence_map(self):
        """ Force the sequence for the init_options so columns headers are already generated but not the columns
            So, between _init_options_column_headers and _init_options_columns"""
        sequence_map = super(AccountReport, self)._get_options_initializers_forced_sequence_map()
        sequence_map[self._init_options_analytic_groupby] = 995
        return sequence_map

    def _init_options_analytic_groupby(self, options, previous_options):
        if not self.filter_analytic_groupby:
            return
        enable_analytic_accounts = self.env.user.has_group('analytic.group_analytic_accounting')
        if not enable_analytic_accounts:
            return

        options['display_analytic_groupby'] = True
        options['display_analytic_plan_groupby'] = True

        options['include_analytic_without_aml'] = previous_options.get('include_analytic_without_aml', False)
        previous_analytic_accounts = previous_options.get('analytic_accounts_groupby', [])
        analytic_account_ids = [int(x) for x in previous_analytic_accounts]
        selected_analytic_accounts = self.env['account.analytic.account'].with_context(active_test=False).search(
            [('id', 'in', analytic_account_ids)])
        options['analytic_accounts_groupby'] = selected_analytic_accounts.ids
        options['selected_analytic_account_groupby_names'] = selected_analytic_accounts.mapped('name')

        previous_analytic_plans = previous_options.get('analytic_plans_groupby', [])
        analytic_plan_ids = [int(x) for x in previous_analytic_plans]
        selected_analytic_plans = self.env['account.analytic.plan'].search([('id', 'in', analytic_plan_ids)])
        options['analytic_plans_groupby'] = selected_analytic_plans.ids
        options['selected_analytic_plan_groupby_names'] = selected_analytic_plans.mapped('name')

        self._create_column_analytic(options)

    def _init_options_readonly_query(self, options, previous_options):
        super()._init_options_readonly_query(options, previous_options)
        options['readonly_query'] = options['readonly_query'] and not options.get('analytic_groupby_option')

    def _create_column_analytic(self, options):
        """ Creates the analytic columns for each plan or account in the filters.
        This will duplicate all previous columns and adding the analytic accounts in the domain of the added columns.

        The analytic_groupby_option is used so the table used is the shadowed table.
        The domain on analytic_distribution can just use simple comparison as the column of the shadowed
        table will simply be filled with analytic_account_ids.
        """
        analytic_headers = []
        plans = self.env['account.analytic.plan'].browse(options.get('analytic_plans_groupby'))
        for plan in plans:
            account_list = []
            accounts = self.env['account.analytic.account'].search([('plan_id', 'child_of', plan.id)])
            for account in accounts:
                account_list.append(account.id)
            analytic_headers.append({
                'name': plan.name,
                'forced_options': {
                    'analytic_groupby_option': True,
                    'analytic_accounts_list': tuple(account_list),  # Analytic accounts used in the domain to filter the lines.
                    'analytic_plan_id': plan.id,
                }
            })

        accounts = self.env['account.analytic.account'].browse(options.get('analytic_accounts_groupby'))
        for account in accounts:
            analytic_headers.append({
                'name': account.name,
                'forced_options': {
                    'analytic_groupby_option': True,
                    'analytic_accounts_list': (account.id,),
                }
            })
        if analytic_headers:
            has_selected_budgets = any([budget for budget in options.get('budgets', []) if budget['selected']])
            if has_selected_budgets:
                # if budget is selected, then analytic headers are placed on the same header level
                options['column_headers'][-1] = analytic_headers + options['column_headers'][-1]
            else:
                # We add the analytic layer to the column_headers before creating the columns
                analytic_headers.append({'name': ''})

                options['column_headers'] = [
                    *options['column_headers'],
                    analytic_headers,
                ]

    @api.model
    def _prepare_lines_for_analytic_groupby(self):
        """Prepare the analytic_temp_account_move_line

        This method should be used once before all the SQL queries using the
        table account_move_line for the analytic columns for the financial reports.
        It will create a new table with the schema of account_move_line table, but with
        the data from account_analytic_line.

        We inherit the schema of account_move_line, make the correspondence between
        account_move_line fields and account_analytic_line fields and put NULL for those
        who don't exist in account_analytic_line.
        We also drop the NOT NULL constraints for fields who are not required in account_analytic_line.
        """
        self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='analytic_temp_account_move_line'")
        if self.env.cr.fetchone():
            return

        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        analytic_cols = SQL(", ").join(SQL('"account_analytic_line".%s', SQL.identifier(n._column_name())) for n in (project_plan + other_plans))
        analytic_distribution_equivalent = SQL('to_jsonb(UNNEST(ARRAY_REMOVE(ARRAY[%s], NULL)))', analytic_cols)

        change_equivalence_dict = {
            'balance': SQL("-amount"),
            'display_type': 'product',
            'parent_state': 'posted',
            'account_id': SQL.identifier("general_account_id"),
            'debit': SQL("CASE WHEN (amount < 0) THEN -amount else 0 END"),
            'credit': SQL("CASE WHEN (amount > 0) THEN amount else 0 END"),
            'analytic_distribution': analytic_distribution_equivalent,
            'date': SQL("account_analytic_line.date"),
            'company_id': SQL("account_analytic_line.company_id"),
        }

        all_stored_aml_fields = {
            field
            for field, attrs in self.env['account.move.line'].fields_get().items()
            if attrs['type'] not in ['many2many', 'one2many'] and attrs.get('store')
        }

        for aml_field in all_stored_aml_fields:
            if aml_field not in change_equivalence_dict:
                change_equivalence_dict[aml_field] = SQL('"account_move_line".%s', SQL.identifier(aml_field))

        stored_aml_fields, fields_to_insert = self.env['account.move.line']._prepare_aml_shadowing_for_report(change_equivalence_dict)

        query = SQL("""
            CREATE OR REPLACE TEMPORARY VIEW analytic_temp_account_move_line (%(stored_aml_fields)s) AS
            SELECT %(fields_to_insert)s
            FROM account_analytic_line
            LEFT JOIN account_move_line
                ON account_analytic_line.move_line_id = account_move_line.id
            WHERE
                account_analytic_line.general_account_id IS NOT NULL;
        """, stored_aml_fields=stored_aml_fields, fields_to_insert=fields_to_insert)

        self.env.cr.execute(query)

    def _get_report_query(self, options, date_scope, domain=None) -> Query:
        # Override to add the context key which will eventually trigger the shadowing of the table
        context_self = self.with_context(account_report_analytic_groupby=options.get('analytic_groupby_option'))

        # We add the domain filter for analytic_distribution here, as the search is not available
        query = super(AccountReport, context_self)._get_report_query(options, date_scope, domain)
        if options.get('analytic_accounts'):
            if 'analytic_accounts_list' in options:
                # the table will be `analytic_temp_account_move_line` and thus analytic_distribution will be a single ID
                analytic_account_ids = tuple(str(account_id) for account_id in options['analytic_accounts'])
                query.add_where(SQL("""account_move_line.analytic_distribution IN %s""", analytic_account_ids))
            else:
                # Real `account_move_line` table so real JSON with percentage
                analytic_account_ids = [[str(account_id) for account_id in options['analytic_accounts']]]
                query.add_where(SQL('%s && %s', analytic_account_ids, self.env['account.move.line']._query_analytic_accounts()))

        return query

    def action_audit_cell(self, options, params):
        column_group_options = self._get_column_group_options(options, params['column_group_key'])

        if not column_group_options.get('analytic_groupby_option'):
            action = super().action_audit_cell(options, params)
            if options.get('column_percent_comparison') == 'analytic_coverage':
                context = ast.literal_eval(action.get('context', "{}"))
                context.update({
                    'selected_analytic_plan': options['analytic_plans_groupby'][0],
                })
                action['context'] = context
                view_id = self.env.ref('account_reports.view_analytic_move_line_tree', raise_if_not_found=False) or False
                if view_id:
                    action['views'] = [(view_id.id, 'list')]
            return action
        else:
            # Start by getting the domain from the options. Note that this domain is targeting account.move.line
            report_line = self.env['account.report.line'].browse(params['report_line_id'])
            expression = report_line.expression_ids.filtered(lambda x: x.label == params['expression_label'])
            line_domain = self._get_audit_line_domain(column_group_options, expression, params)
            # The line domain is made for move lines, so we need some postprocessing to have it work with analytic lines.
            domain = []
            AccountAnalyticLine = self.env['account.analytic.line']
            for expression in line_domain:
                if len(expression) == 1:  # For operators such as '&' or '|' we can juste add them again.
                    domain.append(expression)
                    continue

                field, operator, right_term = expression
                # On analytic lines, the account.account field is named general_account_id and not account_id.
                if field.split('.')[0] == 'account_id':
                    field = field.replace('account_id', 'general_account_id')
                    expression = [(field, operator, right_term)]
                elif field == 'analytic_distribution':
                    if options.get('column_percent_comparison') == 'analytic_coverage':
                        expression = [(1, '=', 1)]
                    else:
                        expression = [('auto_account_id', 'in', right_term)]
                # For other fields not present in on the analytic line model, map them to get the info from the move_line.
                # Or ignore these conditions if there is no move lines.
                elif field.split('.')[0] not in AccountAnalyticLine._fields:
                    expression = [(f'move_line_id.{field}', operator, right_term)]
                    if options.get('include_analytic_without_aml'):
                        expression = osv.expression.OR([
                            [('move_line_id', '=', False)],
                            expression,
                        ])
                else:
                    expression = [expression]  # just for the extend
                domain.extend(expression)

            action = clean_action(self.env.ref('analytic.account_analytic_line_action_entries')._get_action_dict(), env=self.env)
            action['domain'] = domain
            if options.get('column_percent_comparison') == 'analytic_coverage':
                context = ast.literal_eval(action.get('context', "{}"))
                context.update({
                    'selected_analytic_plan': options['analytic_plans_groupby'][0],
                    'group_by': 'move_line_id',
                })
                action['context'] = context
                action['display_name'] += ' - ' + options['selected_analytic_plan_groupby_names'][0]
                view_id = self.env.ref('account_reports.view_analytic_line_tree', raise_if_not_found=False) or False
                if view_id:
                    action['views'] = [(view_id.id, 'list')]

            return action

    @api.model
    def _get_options_journals_domain(self, options):
        domain = super(AccountReport, self)._get_options_journals_domain(options)
        # Add False to the domain in order to select lines without journals for analytics columns.
        if options.get('include_analytic_without_aml'):
            domain = osv.expression.OR([
                domain,
                [('journal_id', '=', False)],
            ])
        return domain

    def _get_options_domain(self, options, date_scope):
        self.ensure_one()
        domain = super()._get_options_domain(options, date_scope)

        # Get the analytic accounts that we need to filter on from the options and add a domain for them.
        if 'analytic_accounts_list' in options:
            domain = osv.expression.AND([
                domain,
                [('analytic_distribution', 'in', options.get('analytic_accounts_list', []))],
            ])

        return domain


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _where_calc(self, domain, active_test=True):
        """ In case we need an analytic column in an account_report, we shadow the account_move_line table
        with a temp table filled with analytic data, that will be used for the analytic columns.
        We do it in this function to only create and fill it once for all computations of a report.
        The following analytic columns and computations will just query the shadowed table instead of the real one.
        """
        query = super()._where_calc(domain, active_test)
        if self.env.context.get('account_report_analytic_groupby') and not self.env.context.get('account_report_cash_basis'):
            self.env['account.report']._prepare_lines_for_analytic_groupby()
            query._tables['account_move_line'] = SQL.identifier('analytic_temp_account_move_line')
        return query
