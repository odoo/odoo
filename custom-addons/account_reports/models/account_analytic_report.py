# Part of Odoo. See LICENSE file for full copyright and licensing details.
from psycopg2 import sql

from odoo import models, fields, api, osv
from odoo.addons.web.controllers.utils import clean_action
from odoo.tools import SQL


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_analytic_groupby = fields.Boolean(
        string="Analytic Group By",
        compute=lambda x: x._compute_report_option_filter('filter_analytic_groupby'), readonly=False, store=True, depends=['root_report_id'],
    )

    def _get_options_initializers_forced_sequence_map(self):
        """ Force the sequence for the init_options so columns headers are already generated but not the columns
            So, between _init_options_column_headers and _init_options_columns"""
        sequence_map = super(AccountReport, self)._get_options_initializers_forced_sequence_map()
        sequence_map[self._init_options_analytic_groupby] = 995
        return sequence_map

    def _init_options_analytic_groupby(self, options, previous_options=None):
        if not self.filter_analytic_groupby:
            return
        enable_analytic_accounts = self.user_has_groups('analytic.group_analytic_accounting')
        if not enable_analytic_accounts:
            return

        options['display_analytic_groupby'] = True
        options['display_analytic_plan_groupby'] = True

        options['include_analytic_without_aml'] = (previous_options or {}).get('include_analytic_without_aml', False)
        previous_analytic_accounts = (previous_options or {}).get('analytic_accounts_groupby', [])
        analytic_account_ids = [int(x) for x in previous_analytic_accounts]
        selected_analytic_accounts = self.env['account.analytic.account'].with_context(active_test=False).search(
            [('id', 'in', analytic_account_ids)])
        options['analytic_accounts_groupby'] = selected_analytic_accounts.ids
        options['selected_analytic_account_groupby_names'] = selected_analytic_accounts.mapped('name')

        previous_analytic_plans = (previous_options or {}).get('analytic_plans_groupby', [])
        analytic_plan_ids = [int(x) for x in previous_analytic_plans]
        selected_analytic_plans = self.env['account.analytic.plan'].search([('id', 'in', analytic_plan_ids)])
        options['analytic_plans_groupby'] = selected_analytic_plans.ids
        options['selected_analytic_plan_groupby_names'] = selected_analytic_plans.mapped('name')

        self._create_column_analytic(options)

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
            analytic_headers.append({'name': ''})
            # We add the analytic layer to the column_headers before creating the columns
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
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name='analytic_temp_account_move_line'")
        if self.env.cr.fetchone():
            return

        line_fields = self.env['account.move.line'].fields_get()
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        stored_fields = set(f[0] for f in self.env.cr.fetchall() if f[0] in line_fields)
        changed_equivalence_dict = {
            "id": sql.Identifier("id"),
            "balance": sql.SQL("-amount"),
            "company_id": sql.Identifier("company_id"),
            "journal_id": sql.Identifier("journal_id"),
            "display_type": sql.Literal("product"),
            "parent_state": sql.Literal("posted"),
            "date": sql.Identifier("date"),
            "account_id": sql.Identifier("general_account_id"),
            "partner_id": sql.Identifier("partner_id"),
            "debit": sql.SQL("CASE WHEN (amount < 0) THEN amount else 0 END"),
            "credit": sql.SQL("CASE WHEN (amount > 0) THEN amount else 0 END"),
        }
        selected_fields = []
        for fname in stored_fields:
            if fname in changed_equivalence_dict:
                selected_fields.append(sql.SQL('{original} AS "account_move_line.{asname}"').format(
                    original=changed_equivalence_dict[fname],
                    asname=sql.SQL(fname),
                ))
            elif fname == 'analytic_distribution':
                project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
                analytic_cols = ", ".join(n._column_name() for n in (project_plan+other_plans))
                selected_fields.append(sql.SQL(f'to_jsonb(UNNEST(ARRAY[{analytic_cols}])) AS "account_move_line.analytic_distribution"'))
            else:
                if line_fields[fname].get("translate"):
                    typecast = sql.SQL('jsonb')
                elif line_fields[fname].get("type") == "monetary":
                    typecast = sql.SQL('numeric')
                elif line_fields[fname].get("type") == "many2one":
                    typecast = sql.SQL('integer')
                elif line_fields[fname].get("type") == "datetime":
                    typecast = sql.SQL('date')
                elif line_fields[fname].get("type") in ["selection", "reference"]:
                    typecast = sql.SQL('text')
                else:
                    typecast = sql.SQL(self.env['account.move.line']._fields[fname].column_type[0])
                selected_fields.append(sql.SQL('cast(NULL AS {typecast}) AS "account_move_line.{fname}"').format(
                    typecast=typecast,
                    fname=sql.SQL(fname),
                ))

        query = sql.SQL("""
            -- Create a temporary table, dropping not null constraints because we're not filling those columns
            CREATE TEMPORARY TABLE IF NOT EXISTS analytic_temp_account_move_line () inherits (account_move_line) ON COMMIT DROP;
            ALTER TABLE analytic_temp_account_move_line NO INHERIT account_move_line;
            ALTER TABLE analytic_temp_account_move_line ALTER COLUMN move_id DROP NOT NULL;
            ALTER TABLE analytic_temp_account_move_line ALTER COLUMN currency_id DROP NOT NULL;

            INSERT INTO analytic_temp_account_move_line ({all_fields})
            SELECT {table}
            FROM (SELECT * FROM account_analytic_line WHERE general_account_id IS NOT NULL) AS account_analytic_line;

            -- Create a supporting index to avoid seq.scans
            CREATE INDEX IF NOT EXISTS analytic_temp_account_move_line__composite_idx ON analytic_temp_account_move_line (analytic_distribution, journal_id, date, company_id);
            -- Update statistics for correct planning
            ANALYZE analytic_temp_account_move_line
        """).format(
            all_fields=sql.SQL(', ').join(sql.Identifier(fname) for fname in stored_fields),
            table=sql.SQL(', ').join(selected_fields),
        )

        self.env.cr.execute(query)

    def _query_get(self, options, date_scope, domain=None):
        # Override to add the context key which will eventually trigger the shadowing of the table
        context_self = self.with_context(account_report_analytic_groupby=options.get('analytic_groupby_option'))

        # We add the domain filter for analytic_distribution here, as the search is not available
        tables, where_clause, where_params = super(AccountReport, context_self)._query_get(options, date_scope, domain)
        if options.get('analytic_accounts'):
            if 'analytic_accounts_list' in options:
                # the table will be `analytic_temp_account_move_line` and thus analytic_distribution will be a single ID
                analytic_account_ids = tuple(str(account_id) for account_id in options['analytic_accounts'])
                where_params.append(analytic_account_ids)
                where_clause = f"""{where_clause} AND "account_move_line".analytic_distribution IN %s"""
            else:
                # Real `account_move_line` table so real JSON with percentage
                analytic_account_ids = [[str(account_id) for account_id in options['analytic_accounts']]]
                where_params.append(analytic_account_ids)
                where_clause = fr"""{where_clause} AND %s && regexp_split_to_array(jsonb_path_query_array("account_move_line".analytic_distribution, '$.keyvalue()."key"')::text, '\D+')"""

        return tables, where_clause, where_params

    def action_audit_cell(self, options, params):
        column_group_options = self._get_column_group_options(options, params['column_group_key'])

        if not column_group_options.get('analytic_groupby_option'):
            return super(AccountReport, self).action_audit_cell(options, params)
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
                # Replace the 'analytic_distribution' by the account_id domain as we expect for analytic lines.
                elif field == 'analytic_distribution':
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
