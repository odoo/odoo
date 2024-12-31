# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.tools import SQL, Query, unique
from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import UserError, ValidationError


class AnalyticMixin(models.AbstractModel):
    _name = 'analytic.mixin'
    _description = 'Analytic Mixin'

    analytic_distribution = fields.Json(
        'Analytic Distribution',
        compute="_compute_analytic_distribution", store=True, copy=True, readonly=False,
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    distribution_analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        compute='_compute_distribution_analytic_account_ids',
        search='_search_distribution_analytic_account_ids',
    )

    def init(self):
        # Add a gin index for json search on the keys, on the models that actually have a table
        query = ''' SELECT table_name
                    FROM information_schema.tables
                    WHERE table_name=%s '''
        self.env.cr.execute(query, [self._table])
        if self.env.cr.dictfetchone() and self._fields['analytic_distribution'].store:
            query = fr"""
                CREATE INDEX IF NOT EXISTS {self._table}_analytic_distribution_accounts_gin_index
                                        ON {self._table} USING gin(regexp_split_to_array(jsonb_path_query_array(analytic_distribution, '$.keyvalue()."key"')::text, '\D+'));
            """
            self.env.cr.execute(query)
        super().init()

    def _compute_analytic_distribution(self):
        pass

    def _query_analytic_accounts(self, table=False):
        return SQL(
            r"""regexp_split_to_array(jsonb_path_query_array(%s, '$.keyvalue()."key"')::text, '\D+')""",
            self._field_to_sql(table or self._table, 'analytic_distribution'),
        )

    @api.depends('analytic_distribution')
    def _compute_distribution_analytic_account_ids(self):
        all_ids = {int(_id) for rec in self for key in (rec.analytic_distribution or {}) for _id in key.split(',')}
        existing_accounts_ids = set(self.env['account.analytic.account'].browse(all_ids).exists().ids)
        for rec in self:
            ids = list(unique(int(_id) for key in (rec.analytic_distribution or {}) for _id in key.split(',') if int(_id) in existing_accounts_ids))
            rec.distribution_analytic_account_ids = self.env['account.analytic.account'].browse(ids)

    def _search_distribution_analytic_account_ids(self, operator, value):
        return [('analytic_distribution', operator, value)]

    def _condition_to_sql(self, alias: str, field_expr: str, operator: str, value, query: Query) -> SQL:
        # Don't use this override when account_report_analytic_groupby is truly in the context
        # Indeed, when account_report_analytic_groupby is in the context it means that `analytic_distribution`
        # doesn't have the same format and the table is a temporary one, see _prepare_lines_for_analytic_groupby
        if field_expr != 'analytic_distribution' or self.env.context.get('account_report_analytic_groupby'):
            return super()._condition_to_sql(alias, field_expr, operator, value, query)

        def search_value(value: str, exact: bool):
            return list(self.env['account.analytic.account']._search(
                [('display_name', ('=' if exact else 'ilike'), value)]
            ))

        # reformulate the condition as <field> in/not in <ids>
        if operator in ('in', 'not in'):
            ids = [
                r
                for v in value
                for r in (search_value(v, exact=True) if isinstance(value, str) else [v])
            ]
        elif operator in ('ilike', 'not ilike'):
            ids = search_value(value, exact=False)
            operator = 'not in' if operator.startswith('not') else 'in'
        else:
            raise UserError(_('Operation not supported'))

        if not ids:
            # not ids found, just call super with an empty list
            return super()._condition_to_sql(alias, field_expr, operator, ids, query)

        if isinstance(value, int) and operator in ('=', '!='):
            value = [value]
            operator = 'in' if operator == '=' else 'not in'

        # keys can be comma-separated ids, we will split those into an array and then make an array comparison with the list of ids to check
        analytic_accounts_query = self._query_analytic_accounts()
        ids = [str(id_) for id_ in ids if id_]  # list of ids -> list of string
        if operator == 'in':
            return SQL(
                "%s && %s",
                analytic_accounts_query,
                ids,
            )
        else:
            return SQL(
                "(NOT %s && %s OR %s IS NULL)",
                analytic_accounts_query,
                ids,
                self._field_to_sql(alias, 'analytic_distribution', query),
            )

    def _read_group_groupby(self, groupby_spec: str, query: Query) -> SQL:
        """To group by `analytic_distribution`, we first need to separate the analytic_ids and associate them with the ids to be counted
        Do note that only '__count' can be passed in the `aggregates`"""
        if groupby_spec == 'analytic_distribution':
            query._tables = {
                'distribution': SQL(
                    r"""(SELECT DISTINCT %s, (regexp_matches(jsonb_object_keys(%s), '\d+', 'g'))[1]::int AS account_id FROM %s WHERE %s)""",
                    self._get_count_id(query),
                    self._field_to_sql(self._table, 'analytic_distribution', query),
                    query.from_clause,
                    query.where_clause,
                )
            }

            # After using the from and where clauses in the nested query, they are no longer needed in the main one
            query._joins = {}
            query._where_clauses = []
            return SQL("account_id")

        return super()._read_group_groupby(groupby_spec, query)

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        if query.table == 'distribution' and aggregate_spec != '__count':
            raise ValueError(f"analytic_distribution grouping does not accept {aggregate_spec} as aggregate.")
        return super()._read_group_select(aggregate_spec, query)

    def _get_count_id(self, query):
        ids = {
            'account_move_line': "move_id",
            'purchase_order_line': "order_id",
            'account_asset': "id",
            'hr_expense': "id",
        }
        if query.table not in ids:
            raise ValueError(f"{query.table} does not support analytic_distribution grouping.")
        return SQL(ids.get(query.table))

    def mapped(self, func):
        # Get the related analytic accounts as a recordset instead of the distribution
        if func == 'analytic_distribution' and self.env.context.get('distribution_ids'):
            func = 'distribution_analytic_account_ids'
        return super().mapped(func)

    def filtered_domain(self, domain):
        # Filter based on the accounts used (i.e. allowing a name_search) instead of the distribution
        # A domain on a binary field doesn't make sense anymore outside of set or not; and it is still doable.
        return super(AnalyticMixin, self.with_context(distribution_ids=True)).filtered_domain(domain)

    def write(self, vals):
        """ Format the analytic_distribution float value, so equality on analytic_distribution can be done """
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        vals = self._sanitize_values(vals, decimal_precision)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """ Format the analytic_distribution float value, so equality on analytic_distribution can be done """
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        vals_list = [self._sanitize_values(vals, decimal_precision) for vals in vals_list]
        return super().create(vals_list)

    def _validate_distribution(self, **kwargs):
        if self.env.context.get('validate_analytic', False):
            mandatory_plans_ids = [plan['id'] for plan in self.env['account.analytic.plan'].sudo().with_company(self.company_id).get_relevant_plans(**kwargs) if plan['applicability'] == 'mandatory']
            if not mandatory_plans_ids:
                return
            decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
            distribution_by_root_plan = {}
            for analytic_account_ids, percentage in (self.analytic_distribution or {}).items():
                for analytic_account in self.env['account.analytic.account'].browse(map(int, analytic_account_ids.split(","))).exists():
                    root_plan = analytic_account.root_plan_id
                    distribution_by_root_plan[root_plan.id] = distribution_by_root_plan.get(root_plan.id, 0) + percentage

            for plan_id in mandatory_plans_ids:
                if float_compare(distribution_by_root_plan.get(plan_id, 0), 100, precision_digits=decimal_precision) != 0:
                    raise ValidationError(_("One or more lines require a 100% analytic distribution."))

    def _sanitize_values(self, vals, decimal_precision):
        """ Normalize the float of the distribution """
        if 'analytic_distribution' in vals:
            vals['analytic_distribution'] = vals.get('analytic_distribution') and {
                account_id: float_round(distribution, decimal_precision) for account_id, distribution in vals['analytic_distribution'].items()}
        return vals
