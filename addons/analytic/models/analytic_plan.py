import re

from odoo import _, api, fields, models
from odoo.db.schema import create_index
from odoo.exceptions import UserError, ValidationError
from odoo.tools import (
    TransactionMemo,
    float_compare,
    float_round,
    frozendict,
    get_index_name,
    ormcache,
)

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG

RELEVANT_PLANS = TransactionMemo(
    "get_relevant_plans",
    invalidated_by={
        "account.analytic.plan": ("default_applicability",),
        "account.analytic.applicability": (),
    },
)


class AccountAnalyticPlan(models.Model):
    _name = "account.analytic.plan"
    _inherit = ["mixin.color"]
    _description = "Analytic Plans"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "sequence asc, id"

    name = fields.Char(
        translate=True,
        inverse="_inverse_name",
        required=True,
    )
    description = fields.Text()
    parent_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        inverse="_inverse_parent_id",
        index="btree_not_null",
        domain="['!', ('id', 'child_of', id)]",
        ondelete="cascade",
    )
    parent_path = fields.Char(index="btree")
    root_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        compute="_compute_root_id",
        search="_search_root_id",
    )
    children_ids = fields.One2many(
        comodel_name="account.analytic.plan",
        inverse_name="parent_id",
        string="Childrens",
    )
    children_count = fields.Count(
        count_of="children_ids",
        string="Children Plans Count",
    )
    complete_name = fields.Char(
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    account_ids = fields.One2many(
        comodel_name="account.analytic.account",
        inverse_name="plan_id",
        string="Accounts",
    )
    account_count = fields.Count(
        count_of="account_ids",
        string="Analytic Accounts Count",
    )
    all_account_count = fields.Integer(
        string="All Analytic Accounts Count",
        compute="_compute_all_account_count",
    )
    color = fields.Integer(default=lambda self: self._default_color())
    sequence = fields.Integer(default=10)

    default_applicability = fields.Selection(
        selection=[
            ("optional", "Optional"),
            ("mandatory", "Mandatory"),
            ("unavailable", "Unavailable"),
        ],
        readonly=False,
        company_dependent=True,
    )
    applicability_ids = fields.One2many(
        comodel_name="account.analytic.applicability",
        inverse_name="analytic_plan_id",
        domain="[('company_id', '=', current_company_id)]",
    )

    def _auto_init(self):
        super()._auto_init()

        def precommit():
            # Only seed the system default once: `_auto_init` reruns on every
            # schema init of this model (every `-i`/`-u` that touches it, not
            # just the first install), and `ir.default.set` unconditionally
            # overwrites an existing row — so an admin's own customization of
            # this default would otherwise be silently reset to "optional" on
            # the next module update.
            if self.env["ir.default"]._get(self._name, "default_applicability") is None:
                self.env["ir.default"].set(
                    self._name,
                    "default_applicability",
                    "optional",
                )

        self.env.cr.precommit.add(precommit)

    @ormcache()
    def __get_all_plans(self):
        project_plan = self.browse(
            int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("analytic.project_plan", 0)
            )
        )
        if not project_plan:
            raise UserError(
                _(
                    "A 'Project' plan needs to exist and its id needs to be set as `analytic.project_plan` in the system variables"
                )
            )
        other_plans = self.sudo().search([("parent_id", "=", False)]) - project_plan
        return project_plan.id, other_plans.ids

    def _get_all_plans(self):
        return map(self.browse, self.__get_all_plans())

    def _strict_column_name(self):
        self.check_singleton()
        project_plan, _other_plans = self._get_all_plans()
        return "account_id" if self == project_plan else f"x_plan{self.id}_id"

    def _column_name(self):
        return self.root_id._strict_column_name()

    def _inverse_name(self):
        self._sync_all_plan_column()

    def _inverse_parent_id(self):
        self._sync_all_plan_column()

    @api.depends("parent_id", "parent_path")
    def _compute_root_id(self):
        for plan in self.sudo():
            plan.root_id = plan._get_root()

    def _search_root_id(self, operator, value):
        if operator != "=":
            return NotImplemented
        return [("parent_path", "=like", f"{value}/%")]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for plan in self:
            if plan.parent_id:
                plan.complete_name = "%s / %s" % (
                    plan.parent_id.complete_name,
                    plan.name,
                )
            else:
                plan.complete_name = plan.name

    @api.depends("account_ids", "children_ids")
    def _compute_all_account_count(self):
        # Get all children_ids from each plan
        if not self.ids:
            self.all_account_count = 0
            return
        self.env.cr.execute(
            """
            SELECT parent.id,
                   array_agg(child.id) as children_ids
              FROM account_analytic_plan parent
              JOIN account_analytic_plan child ON child.parent_path LIKE parent.parent_path || '%%'
             WHERE parent.id = ANY(%s)
          GROUP BY parent.id
        """,
            [list(self.ids)],
        )
        all_children_ids = dict(self.env.cr.fetchall())

        plans_count = dict(
            self.env["account.analytic.account"]._read_group(
                domain=[("plan_id", "child_of", self.ids)],
                aggregates=["id:count"],
                groupby=["plan_id"],
            )
        )
        plans_count = {k.id: v for k, v in plans_count.items()}
        for plan in self:
            plan.all_account_count = sum(
                plans_count.get(child_id, 0)
                for child_id in all_children_ids.get(plan.id, [])
            )

    @api.onchange("parent_id")
    def _onchange_parent_id(self):
        project_plan, __ = self._get_all_plans()
        if self._origin.id == project_plan.id:
            raise UserError(
                _("You cannot add a parent to the base plan '%s'", project_plan.name)
            )

    @api.constrains("parent_id")
    def _check_project_plan_has_no_parent(self):
        # Companion check to `_onchange_parent_id`: the onchange only guards the
        # form UI, so a direct write()/create() (RPC, scripts, other modules)
        # could still reparent the "Project" plan referenced by
        # `analytic.project_plan` and silently invalidate `root_id`/
        # `_column_name()` for every model using `auto_account_id`.
        project_plan, __ = self._get_all_plans()
        if project_plan in self and project_plan.parent_id:
            raise ValidationError(
                _("You cannot add a parent to the base plan '%s'", project_plan.name)
            )

    def action_view_analytical_accounts(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "domain": [("plan_id", "child_of", self.id)],
            "context": {"default_plan_id": self.id},
            "name": _("Analytical Accounts"),
            "view_mode": "list,form",
        }

    def action_view_children_plans(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.plan",
            "domain": [("parent_id", "=", self.id)],
            "context": {"default_parent_id": self.id, "default_color": self.color},
            "name": _("Analytical Plans"),
            "view_mode": "list,form",
        }

    @api.model
    def get_relevant_plans(self, **kwargs):
        """Returns the list of plans that should be available.
        This list is computed based on the applicabilities of root plans."""
        cache = RELEVANT_PLANS(self.env)
        # `default_applicability` is `company_dependent`, so the result also
        # depends on the active company even when `kwargs` doesn't carry a
        # `company_id` — key the cache on it too, or two calls for different
        # companies in the same request/cursor silently reuse each other's result.
        key = frozendict(kwargs, __company_ids__=tuple(self.env.companies.ids))
        if key in cache:
            return cache[key]
        record_account_ids = kwargs.get("existing_account_ids", [])
        project_plan, other_plans = self.env["account.analytic.plan"]._get_all_plans()
        root_plans = (project_plan + other_plans).filtered(
            lambda p: (
                p.all_account_count > 0
                and not p.parent_id
                and p._get_applicability(**kwargs) != "unavailable"
            )
        )
        # If we have accounts that are already selected (before the applicability rules changed or from a model),
        # we want the plans that were unavailable to be shown in the list (and in optional, because the previous
        # percentage could be different from 0)
        forced_plans = (
            self.env["account.analytic.account"]
            .browse(record_account_ids)
            .exists()
            .mapped("root_plan_id")
            - root_plans
        )
        cache[key] = [
            {
                "id": plan.id,
                "name": plan.name,
                "color": plan.color,
                "applicability": plan._get_applicability(**kwargs)
                if plan in root_plans
                else "optional",
                "all_account_count": plan.all_account_count,
                "column_name": plan._column_name(),
            }
            for plan in (root_plans + forced_plans).sorted("sequence")
        ]
        return cache[key]

    def _get_applicability(self, **kwargs):
        """Returns the applicability of the best applicability line or the default applicability"""
        self.check_singleton()
        if "applicability" in kwargs:
            # For models for example, we want all plans to be visible, so we force the applicability
            return kwargs["applicability"]
        else:
            score = 0
            applicability = self.default_applicability
            for applicability_rule in self.applicability_ids.filtered(
                lambda rule: (
                    not rule.company_id
                    or not kwargs.get("company_id")
                    or rule.company_id.id == kwargs.get("company_id")
                )
            ):
                score_rule = applicability_rule._get_score(**kwargs)
                if score_rule > score:
                    applicability = applicability_rule.applicability
                    score = score_rule
            return applicability

    def unlink(self):
        # Remove the dynamic field created with the plan (see `_inverse_name`)
        self._get_plan_column().unlink()
        related_fields = self._get_related_field()
        res = super().unlink()
        related_fields.filtered(lambda f: not self._is_subplan_field_used(f)).unlink()
        self.env.registry.clear_cache("stable")
        return res

    def _hierarchy_name(self):
        depth = self.parent_path.count("/") - 1
        fname = f"{self._column_name()}_{depth}"
        if fname.startswith("account_id"):
            fname = f"x_{fname}"
        return depth, fname

    def _is_subplan_field_used(self, field):
        """Return `True` if there are analytic plans still on the same hierarchy level as what the field was created for.

        :param field: the recordset of a field created to group by sub plan
        :rtype: bool
        """
        assert "_id_" in field.name
        root_name, depth = field.name.rsplit("_", maxsplit=1)
        plan_id_match = re.search(r"\d+", root_name)
        plan_id = int(
            plan_id_match.group() if plan_id_match else next(self._get_all_plans())
        )
        return bool(
            self.env["account.analytic.plan"].search(
                [
                    ("root_id", "=", plan_id),
                    ("parent_path", "like", "%".join("/" * (int(depth) + 1))),
                ]
            )
        )

    def _get_plan_column(self, model=False):
        domain = [("name", "in", [plan._strict_column_name() for plan in self])]
        if model:
            domain.append(("model", "=", model))
        return self.env["ir.model.fields"].sudo().search(domain)

    def _get_related_field(self, model=False):
        domain = [("name", "in", [plan._hierarchy_name()[1] for plan in self])]
        if model:
            domain.append(("model", "=", model))
        return self.env["ir.model.fields"].sudo().search(domain)

    def _sync_all_plan_column(self):
        model_names = self.env.registry.get_descendants(
            ["mixin.analytic.plan.fields"], "_inherit"
        ) - {"mixin.analytic.plan.fields"}
        for model in model_names:
            self._sync_plan_column(model)

    def _sync_plan_column(self, model):
        # Create/delete a new field/column on related models for this plan, and keep the name in sync.
        # Sort by parent_path to ensure parents are processed before children
        for plan in self.sorted("parent_path"):
            prev_stored = plan._get_plan_column(model)
            depth, name_related = plan._hierarchy_name()
            prev_related = plan._get_related_field(model)
            if plan.parent_id:
                # If there is a parent, we just need to make sure there is a field to group by the hierarchy level
                # of this plan, allowing to group by sub plan
                if prev_stored:
                    prev_stored.with_context({MODULE_UNINSTALL_FLAG: True}).unlink()
                description = f"{plan.root_id.name} ({depth})"
                if not prev_related:
                    self.env["ir.model.fields"].with_context(
                        update_custom_fields=True
                    ).sudo().create(
                        {
                            "name": name_related,
                            "field_description": description,
                            "state": "manual",
                            "model": model,
                            "model_id": self.env["ir.model"]._get_id(model),
                            "ttype": "many2one",
                            "relation": "account.analytic.plan",
                            "related": plan._column_name()
                            + ".plan_id"
                            + ".parent_id" * (depth - 1),
                            "store": False,
                            "readonly": True,
                        }
                    )
                else:
                    prev_related.field_description = description
            else:
                # If there is no parent, then we need to create a new stored field as this is the root plan
                if prev_related:
                    prev_related.with_context({MODULE_UNINSTALL_FLAG: True}).unlink()
                description = plan.name
                if not prev_stored:
                    column = plan._strict_column_name()
                    field = (
                        self.env["ir.model.fields"]
                        .with_context(update_custom_fields=True)
                        .sudo()
                        .create(
                            {
                                "name": column,
                                "field_description": description,
                                "state": "manual",
                                "model": model,
                                "model_id": self.env["ir.model"]._get_id(model),
                                "ttype": "many2one",
                                "relation": "account.analytic.account",
                                "copied": True,
                                "on_delete": "restrict",
                            }
                        )
                    )
                    Model = self.env[model]
                    if Model._auto:
                        tablename = Model._table
                        indexname = get_index_name(tablename, column)
                        create_index(
                            self.env.cr,
                            indexname,
                            tablename,
                            [column],
                            "btree",
                            f"{column} IS NOT NULL",
                        )
                        field["index"] = True
                else:
                    prev_stored.field_description = description
        if self.children_ids:
            self.children_ids._sync_plan_column(model)

    def write(self, vals):
        new_parent = self.env["account.analytic.plan"].browse(vals.get("parent_id"))
        plan2previous_parent = {plan: plan.parent_id for plan in self if plan.parent_id}
        if "parent_id" in vals and new_parent:
            # Update accounts in analytic lines before _sync_plan_column() unlinks child plan's column
            for plan in self:
                self.env["account.analytic.account"]._update_accounts_in_analytic_lines(
                    new_fname=new_parent._column_name(),
                    current_fname=plan._column_name(),
                    accounts=self.env["account.analytic.account"].search(  # noqa: E8507 - one query per plan: the plan names the column to move
                        [("plan_id", "child_of", plan.id)]
                    ),
                )

        res = super().write(vals)

        if "parent_id" in vals and not new_parent:
            # Update accounts in analytic lines after _sync_plan_column() creates the new column
            for plan, previous_parent in plan2previous_parent.items():
                self.env["account.analytic.account"]._update_accounts_in_analytic_lines(
                    new_fname=plan._column_name(),
                    current_fname=previous_parent._column_name(),
                    accounts=self.env["account.analytic.account"].search(  # noqa: E8507 - one query per plan: the plan names the column to move
                        [("plan_id", "child_of", plan.id)]
                    ),
                )
        return res

    def _get_distribution_amount(
        self, amount, percentage, total_percentage, distribution_on_each_plan
    ):
        """
        Ensures that the total amount distributed across all lines always adds up to exactly `amount` per
        plan. We try to correct for compounding rounding errors by assigning the exact outstanding amount when
        we detect that a line will close out a plan's total percentage. However, since multiple plans can be
        assigned to a line, with different prior distributions, there is the possible edge case that one line
        closes out two (or more) tallies with different compounding errors. This means there is no one correct
        amount that we can assign to a line that will correctly close out both all plans. This is described in
        more detail in the commit message, under "concurrent closing line edge case".

        :param amount:                      the total amount to distribute
        :param percentage:                  this line's share of the distribution, as a percentage
        :param total_percentage:            the percentage this plan's distribution should add up to
        :param distribution_on_each_plan:   accumulator dict, keyed by plan, mutated in place to track
                                            progress toward each plan's total_percentage
        :return: the amount to assign to this line for this plan
        :rtype:   float
        """
        decimal_precision = self.env["decimal.precision"].get_precision(
            "Percentage Analytic"
        )
        distributed_percentage, distributed_amount = distribution_on_each_plan.get(
            self, (0, 0)
        )
        allocated_percentage = distributed_percentage + percentage
        if (
            float_compare(
                allocated_percentage,
                total_percentage,
                precision_digits=decimal_precision,
            )
            == 0
        ):
            calculated_amount = (amount * total_percentage / 100) - distributed_amount
        else:
            calculated_amount = amount * percentage / 100
        distributed_amount += float_round(
            calculated_amount, precision_digits=decimal_precision
        )
        distribution_on_each_plan[self] = (allocated_percentage, distributed_amount)
        return calculated_amount


class AccountAnalyticApplicability(models.Model):
    _name = "account.analytic.applicability"
    _description = "Analytic Plan's Applicabilities"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    analytic_plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        index="btree_not_null",
    )
    business_domain = fields.Selection(
        selection=[
            ("general", "Miscellaneous"),
        ],
        string="Domain",
        required=True,
    )
    applicability = fields.Selection(
        selection=[
            ("optional", "Optional"),
            ("mandatory", "Mandatory"),
            ("unavailable", "Unavailable"),
        ],
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    def _get_score(self, **kwargs):
        """Gives the score of an applicability with the parameters of kwargs"""
        self.check_singleton()
        # 0.5 is because company is less important than other fields for an equal number of valid fields
        # No company on the applicability and the kwargs together are not considered a more fitting rule
        score = 0.5 if self.company_id and kwargs.get("company_id") else 0
        if not kwargs.get("business_domain"):
            return score
        else:
            return (
                score + 1
                if kwargs.get("business_domain") == self.business_domain
                else -1
            )
