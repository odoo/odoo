# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.tools import SQL, Query
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

    def init(self):
        # Add a gin index for json search on the keys, on the models that actually have a table
        query = ''' SELECT table_name
                    FROM information_schema.tables
                    WHERE table_name=%s '''
        self.env.cr.execute(query, [self._table])
        if self.env.cr.dictfetchone() and self._fields['analytic_distribution'].store:
            query = f"""
                CREATE INDEX IF NOT EXISTS {self._table}_analytic_distribution_gin_index
                                        ON {self._table} USING gin(analytic_distribution);
            """
            self.env.cr.execute(query)
        super().init()

    def _compute_analytic_distribution(self):
        pass

    def _condition_to_sql(self, alias: str, fname: str, operator: str, value, query: Query) -> SQL:
        # Don't use this override when account_report_analytic_groupby is truly in the context
        # Indeed, when account_report_analytic_groupby is in the context it means that `analytic_distribution`
        # doesn't have the same format and the table is a temporary one, see _prepare_lines_for_analytic_groupby
        if fname != 'analytic_distribution' or self.env.context.get('account_report_analytic_groupby'):
            return super()._condition_to_sql(alias, fname, operator, value, query)

        if operator not in ('=', '!=', 'ilike', 'not ilike', 'in', 'not in'):
            raise UserError(_('Operation not supported'))

        if operator in ('=', '!=') and isinstance(value, bool):
            return super()._condition_to_sql(alias, fname, operator, value, query)

        if isinstance(value, str) and operator in ('=', '!=', 'ilike', 'not ilike'):
            value = list(self.env['account.analytic.account']._name_search(
                name=value, operator=('=' if operator in ('=', '!=') else 'ilike'),
            ))
            operator = 'in' if operator in ('=', 'ilike') else 'not in'

        analytic_distribution_sql = self._field_to_sql(alias, 'analytic_distribution', query)
        value = [str(id_) for id_ in value if id_]  # list of ids -> list of string
        if operator == 'in':  # 'in' -> ?|
            return SQL(
                "%s ?| ARRAY[%s]",
                analytic_distribution_sql,
                value,
            )
        if operator == 'not in':
            return SQL(
                "(NOT %s ?| ARRAY[%s] OR %s IS NULL)",
                analytic_distribution_sql,
                value,
                analytic_distribution_sql,
            )
        raise UserError(_('Operation not supported'))

    def _read_group_groupby(self, groupby_spec: str, query: Query) -> SQL:
        if groupby_spec == 'analytic_distribution':
            return SQL(
                'jsonb_object_keys(%s)',
                self._field_to_sql(self._table, 'analytic_distribution', query),
            )
        return super()._read_group_groupby(groupby_spec, query)

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

    def _get_analytic_account_ids(self) -> list[int]:
        """ Get the analytic account ids from the analytic_distribution dict """
        self.ensure_one()
        return [int(account_id) for ids in self.analytic_distribution for account_id in ids.split(',')]
