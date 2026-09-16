from collections import defaultdict

from odoo import _, api, fields, models
from odoo.db.schema import table_exists
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.numbers import float_compare, float_round
from odoo.tools import SQL, Query


class MixinAnalytic(models.AbstractModel):
    _name = "mixin.analytic"
    _description = "Analytic Mixin"

    analytic_distribution = fields.Json(
        compute="_compute_analytic_distribution",
        search="_search_analytic_distribution",
        store=True,
        copy=True,
        readonly=False,
    )
    analytic_precision = fields.Integer(
        default=lambda self: self.env["decimal.precision"].get_precision(
            "Percentage Analytic"
        ),
        store=False,
    )
    distribution_analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        compute="_compute_distribution_analytic_account_ids",
        search="_search_distribution_analytic_account_ids",
    )

    def init(self):
        # Add a gin index for json search on the keys, on the models that actually have a table
        if (
            table_exists(self.env.cr, self._table)
            and self._fields["analytic_distribution"].store
        ):
            query = rf"""
                CREATE INDEX IF NOT EXISTS {self._table}_analytic_distribution_accounts_gin_index
                                        ON {self._table} USING gin(regexp_split_to_array(jsonb_path_query_array(analytic_distribution, '$.keyvalue()."key"')::text, '\D+'));
            """
            self.env.cr.execute(query)
        super().init()

    def _query_analytic_accounts(self, table=False):
        return SQL(
            r"""regexp_split_to_array(jsonb_path_query_array(%s, '$.keyvalue()."key"')::text, '\D+')""",
            self._field_to_sql(table or self._table, "analytic_distribution"),
        )

    @api.model
    def _account_ids_from_distribution(self, distribution):
        """Return the de-duplicated analytic account ids of one distribution dict.

        :param distribution: mapping of distribution keys to percentages
        :return: account ids in order of first appearance
        :rtype: list
        """
        # Non-numeric key segments (the transient ``__update__`` marker, a
        # trailing comma, whitespace padding) are skipped, so a malformed
        # distribution never raises a raw ``ValueError`` when its keys are parsed.
        ordered = {}
        for key in distribution or ():
            for segment in str(key).split(","):
                segment = segment.strip()
                if segment.isdigit():
                    ordered.setdefault(int(segment), None)
        return list(ordered)

    @api.model
    def _get_analytic_account_ids_from_distributions(self, distributions):
        if not distributions:
            return set()
        if not isinstance(distributions, (list, tuple, set)):
            distributions = [distributions]
        return {
            account_id
            for distribution in distributions
            for account_id in self._account_ids_from_distribution(distribution)
        }

    @api.depends("analytic_distribution")
    def _compute_distribution_analytic_account_ids(self):
        all_ids = self._get_analytic_account_ids_from_distributions(
            [rec.analytic_distribution for rec in self]
        )
        existing_accounts_ids = set(
            self.env["account.analytic.account"].browse(all_ids).exists().ids
        )
        for rec in self:
            ids = [
                aid
                for aid in self._account_ids_from_distribution(
                    rec.analytic_distribution
                )
                if aid in existing_accounts_ids
            ]
            rec.distribution_analytic_account_ids = self.env[
                "account.analytic.account"
            ].browse(ids)

    def _search_distribution_analytic_account_ids(self, operator, value):
        if operator in ("any", "not any", "any!", "not any!"):
            if isinstance(value, Domain):
                value = self.env["account.analytic.account"].search(value).ids
            elif isinstance(value, Query):
                value = value.get_result_ids()
            else:
                return NotImplemented
            operator = "in" if operator in ("any", "any!") else "not in"
        return [("analytic_distribution", operator, value)]

    def _compute_analytic_distribution(self):
        pass

    def _search_analytic_distribution(self, operator, value):
        # When account_report_analytic_groupby is in the context, `analytic_distribution`
        # is not the real column: the query runs against the shadowed table built by
        # _create_aml_shadowing_query_for_analytic_groupby, where the column holds a
        # single analytic account id as a jsonb scalar (to_jsonb(int)). The generic
        # Json-field search binds the compared ids as psycopg `json`, and PostgreSQL
        # has no `jsonb = json` operator (this fork runs psycopg3), so the comparison
        # must be spelled out against jsonb values explicitly.
        if self.env.context.get("account_report_analytic_groupby"):
            if operator not in ("in", "not in"):
                raise UserError(_("Operation not supported"))
            # to_jsonb(<int account id>) renders as the jsonb number '5'; casting the
            # searched ids through text to jsonb ('5'::jsonb) yields the same value.
            jsonb_ids = [str(int(v)) for v in value if v is not False]
            sql_template = (
                "%s = ANY(%s::jsonb[])"
                if operator == "in"
                else "NOT (%s = ANY(%s::jsonb[]))"
            )
            return Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    sql_template,
                    model._field_to_sql(alias, "analytic_distribution", query),
                    jsonb_ids,
                )
            )
        # Don't use this override for the "is set / not set" checks.
        if operator in ("in", "not in") and False in value:
            return Domain("analytic_distribution", operator, value)

        def search_value(value: str, exact: bool):
            return list(
                self.env["account.analytic.account"]._search(
                    [("display_name", ("=" if exact else "ilike"), value)]
                )
            )

        # reformulate the condition as <field> in/not in <ids>
        if operator in ("in", "not in"):
            ids = [
                r
                for v in value
                for r in (search_value(v, exact=True) if isinstance(v, str) else [v])
            ]
        elif operator in ("ilike", "not ilike"):
            ids = search_value(value, exact=False)
            operator = "not in" if operator.startswith("not") else "in"
        else:
            raise UserError(_("Operation not supported"))

        if not ids:
            # not ids found, just let it optimize to a constant
            return Domain(operator == "not in")

        # keys can be comma-separated ids, we will split those into an array and then make an array comparison with the list of ids to check
        ids = [str(id_) for id_ in ids if id_]  # list of ids -> list of string
        if operator == "in":
            return Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "%s && %s",
                    self._query_analytic_accounts(alias),
                    ids,
                )
            )
        else:
            return Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "(NOT %s && %s OR %s IS NULL)",
                    self._query_analytic_accounts(alias),
                    ids,
                    model._field_to_sql(alias, "analytic_distribution", query),
                )
            )

    def _read_group_groupby(self, alias: str, groupby_spec: str, query: Query) -> SQL:
        """Group by ``analytic_distribution`` by splitting it into one row per account.

        :rtype: SQL
        """
        # Only '__count' can be passed in the `aggregates` (see `_read_group_select`).
        if groupby_spec == "analytic_distribution":
            query._tables = {
                "distribution": SQL(
                    r"""(SELECT DISTINCT %s, (regexp_matches(jsonb_object_keys(%s), '\d+', 'g'))[1]::int AS account_id FROM %s WHERE %s)""",
                    self._get_count_id(query),
                    self._field_to_sql(self._table, "analytic_distribution", query),
                    query.from_clause,
                    query.where_clause,
                )
            }

            # After using the from and where clauses in the nested query, they are no longer needed in the main one
            query._joins = {}
            query._where_clauses = []
            return SQL("account_id")

        return super()._read_group_groupby(alias, groupby_spec, query)

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        if query.table == "distribution" and aggregate_spec != "__count":
            raise ValueError(
                f"analytic_distribution grouping does not accept {aggregate_spec} as aggregate."
            )
        return super()._read_group_select(aggregate_spec, query)

    def _get_count_id(self, query):
        """Return the entity counted when grouping by ``analytic_distribution``.

        :rtype: SQL
        """
        # Overridable hook: a model that would rather count a parent document
        # (e.g. journal entries instead of journal items) overrides it, so the
        # base `analytic` module needs no knowledge of the tables of the modules
        # depending on it.
        return SQL("id")

    def filtered_domain(self, domain):
        # Filter based on the accounts used (i.e. allowing a name_search) instead of the distribution
        # A domain on a json field doesn't make sense anymore outside of set or not; and it is still doable.
        # Hack to filter using another field.
        domain = Domain(domain).map_conditions(
            lambda cond: (
                Domain("distribution_analytic_account_ids", cond.operator, cond.value)
                if cond.field_expr == "analytic_distribution"
                else cond
            )
        )
        return super().filtered_domain(domain)

    def write(self, vals):
        """Format the analytic_distribution float value, so equality on analytic_distribution can be done"""
        decimal_precision = self.env["decimal.precision"].get_precision(
            "Percentage Analytic"
        )
        vals = self._normalize_values(vals, decimal_precision)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Format the analytic_distribution float value, so equality on analytic_distribution can be done"""
        decimal_precision = self.env["decimal.precision"].get_precision(
            "Percentage Analytic"
        )
        vals_list = [
            self._normalize_values(vals, decimal_precision) for vals in vals_list
        ]
        return super().create(vals_list)

    def _check_distribution(self, **kwargs):
        if self.env.context.get("validate_analytic", False):
            mandatory_plans_ids = [
                plan["id"]
                for plan in self.env["account.analytic.plan"]
                .sudo()
                .with_company(self.company_id)
                .get_relevant_plans(**kwargs)
                if plan["applicability"] == "mandatory"
            ]
            if not mandatory_plans_ids:
                return
            decimal_precision = self.env["decimal.precision"].get_precision(
                "Percentage Analytic"
            )
            distribution_by_root_plan = {}
            for analytic_account_ids, percentage in (
                self.analytic_distribution or {}
            ).items():
                account_ids = self._account_ids_from_distribution(
                    {analytic_account_ids: percentage}
                )
                for analytic_account in (
                    self.env["account.analytic.account"].browse(account_ids).exists()
                ):
                    root_plan = analytic_account.root_plan_id
                    distribution_by_root_plan[root_plan.id] = (
                        distribution_by_root_plan.get(root_plan.id, 0) + percentage
                    )

            for plan_id in mandatory_plans_ids:
                if (
                    float_compare(
                        distribution_by_root_plan.get(plan_id, 0),
                        100,
                        precision_digits=decimal_precision,
                    )
                    != 0
                ):
                    raise ValidationError(
                        _("One or more lines require a 100% analytic distribution.")
                    )

    def _analytic_distribution_consumes_update(self):
        """Return whether this model's write path merges the ``__update__`` marker.

        :rtype: bool
        """
        # Only models that actually consume the marker (via `_merge_distribution`)
        # may let it reach persistence; for every other model it is stripped in
        # `_normalize_values` so it never corrupts the stored JSON.
        return False

    def _normalize_values(self, vals, decimal_precision):
        """Normalize the distribution floats and drop the unused ``__update__`` marker"""
        if "analytic_distribution" in vals:
            distribution = vals.get("analytic_distribution")
            if (
                distribution
                and "__update__" in distribution
                and not self._analytic_distribution_consumes_update()
            ):
                distribution = {
                    key: value
                    for key, value in distribution.items()
                    if key != "__update__"
                }
            vals["analytic_distribution"] = distribution and {
                account_id: float_round(value, decimal_precision)
                if account_id != "__update__"
                else value
                for account_id, value in distribution.items()
            }
        return vals

    def _modifiying_distribution_values(self, old_distribution, new_distribution):
        fnames_to_update = set(new_distribution.pop("__update__", ()))
        if old_distribution:
            old_distribution.pop("__update__", None)  # might be set before in `create`
        project_plan, other_plans = self.env["account.analytic.plan"]._get_all_plans()
        non_changing_plans = {
            plan
            for plan in project_plan + other_plans
            if plan._column_name() not in fnames_to_update
        }

        non_changing_values = defaultdict(float)
        non_changing_amount = 0
        for old_key, old_val in old_distribution.items():
            remaining_key = tuple(
                sorted(
                    account.id
                    for account in self.env["account.analytic.account"].browse(
                        int(aid) for aid in old_key.split(",")
                    )
                    if account.plan_id.root_id in non_changing_plans
                )
            )
            if remaining_key:
                non_changing_values[remaining_key] += old_val
                non_changing_amount += old_val

        changing_values = defaultdict(float)
        changing_amount = 0
        for new_key, new_val in new_distribution.items():
            remaining_key = tuple(
                sorted(
                    account.id
                    for account in self.env["account.analytic.account"].browse(
                        int(aid) for aid in new_key.split(",")
                    )
                    if account.plan_id.root_id not in non_changing_plans
                )
            )
            if remaining_key:
                changing_values[remaining_key] += new_val
                changing_amount += new_val

        return (
            non_changing_values,
            changing_values,
            non_changing_amount,
            changing_amount,
        )

    def _merge_distribution(
        self, old_distribution: dict, new_distribution: dict
    ) -> dict:
        if "__update__" not in new_distribution:
            return new_distribution  # update everything by default

        non_changing_values, changing_values, non_changing_amount, changing_amount = (
            self._modifiying_distribution_values(
                old_distribution,
                new_distribution,
            )
        )
        if non_changing_amount > changing_amount:
            ratio = changing_amount / non_changing_amount
            additional_vals = {
                ",".join(map(str, old_key)): old_val * (1 - ratio)
                for old_key, old_val in non_changing_values.items()
                if old_key
            }
            ratio = 1
        elif changing_amount > non_changing_amount:
            ratio = non_changing_amount / changing_amount
            additional_vals = {
                ",".join(map(str, new_key)): new_val * (1 - ratio)
                for new_key, new_val in changing_values.items()
                if new_key
            }
        else:
            ratio = 1
            additional_vals = {}

        return {
            ",".join(map(str, old_key + new_key)): ratio
            * old_val
            * new_val
            / non_changing_amount
            if non_changing_amount
            else 0
            for old_key, old_val in non_changing_values.items()
            for new_key, new_val in changing_values.items()
        } | additional_vals
