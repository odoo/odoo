# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.tools import SQL
from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import UserError, ValidationError

class AnalyticMixin(models.AbstractModel):
    _name = 'analytic.mixin'
    _description = 'Analytic Mixin'

    analytic_distribution = fields.Json(
        'Analytic Distribution',
        compute="_compute_analytic_distribution", store=True, copy=True, readonly=False,
    )
    # Json non stored to be able to search on analytic_distribution.
    analytic_distribution_search = fields.Json(
        store=False,
        search="_search_analytic_distribution"
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
            query = fr"""
                CREATE INDEX IF NOT EXISTS {self._table}_analytic_distribution_accounts_gin_index
                                        ON {self._table} USING gin(regexp_split_to_array(jsonb_path_query_array(analytic_distribution, '$.keyvalue()."key"')::text, '\D+'));
            """
            self.env.cr.execute(query)
        super().init()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ Hide analytic_distribution_search from filterable/searchable fields"""
        res = super().fields_get(allfields, attributes)
        if res.get('analytic_distribution_search'):
            res['analytic_distribution_search']['searchable'] = False
        return res

    def _compute_analytic_distribution(self):
        pass

    def _search_analytic_distribution(self, operator, value):
        if operator == 'in' and isinstance(value, (tuple, list)):
            account_ids = value
            operator_inselect = 'inselect'
        elif operator in ('=', '!=', 'ilike', 'not ilike') and isinstance(value, (str, bool)):
            operator_name_search = '=' if operator in ('=', '!=') else 'ilike'
            account_ids = list(self.env['account.analytic.account']._name_search(name=value, operator=operator_name_search))
            operator_inselect = 'inselect' if operator in ('=', 'ilike') else 'not inselect'
        else:
            raise UserError(_('Operation not supported'))

        query = SQL(
            fr"""
            SELECT id
            FROM {self._table}
            WHERE %s && %s
            """,
            [str(account_id) for account_id in account_ids],
            self._query_analytic_accounts(),
        )

        return [('id', operator_inselect, query)]

    def _query_analytic_accounts(self, table=False):
        return SQL(
            r"""regexp_split_to_array(jsonb_path_query_array(%s.analytic_distribution, '$.keyvalue()."key"')::text, '\D+')""",
            SQL(table or self._table),
        )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        domain = self._apply_analytic_distribution_domain(domain)
        return super()._search(domain, offset, limit, order, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = self._apply_analytic_distribution_domain(domain)
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

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

    def _apply_analytic_distribution_domain(self, domain):
        return [
            ('analytic_distribution_search', leaf[1], leaf[2]) if len(leaf) == 3 and leaf[0] == 'analytic_distribution' and isinstance(leaf[2], (str, tuple, list)) else leaf
            for leaf in domain
        ]

    def _get_analytic_account_ids(self) -> list[int]:
        """ Get the analytic account ids from the analytic_distribution dict """
        self.ensure_one()
        return [int(account_id) for ids in self.analytic_distribution for account_id in ids.split(',')]
