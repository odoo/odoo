from itertools import starmap

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL, TransactionMemo

CANDIDATE_MODELS = TransactionMemo(
    "analytic.distribution.model.candidates",
    invalidated_by=("account.analytic.distribution.model",),
)


class AccountAnalyticDistributionModel(models.Model):
    _name = "account.analytic.distribution.model"
    _inherit = ["mixin.analytic"]
    _description = "Analytic Distribution Model"
    _rec_name = "create_date"
    _order = "sequence, id desc"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        ondelete="cascade",
        help="Select a partner for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)",
    )
    partner_tag_id = fields.Many2one(
        comodel_name="res.partner.tag",
        ondelete="cascade",
        help="Select a partner tag for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        ondelete="cascade",
        help="Select a company for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)",
    )

    @api.constrains("company_id")
    def _check_company_accounts(self):
        """Ensure accounts specific to a company isn't used in any distribution model that wouldn't be specific to the company"""
        query = SQL(
            """
            SELECT model.id
              FROM account_analytic_distribution_model model
              JOIN account_analytic_account account
                ON ARRAY[account.id::text] && %s
             WHERE account.company_id IS NOT NULL AND model.id = ANY(%s)
               AND (model.company_id IS NULL
                OR model.company_id != account.company_id)
            """,
            self._query_analytic_accounts("model"),
            self.ids,
        )
        self.flush_model(["company_id", "analytic_distribution"])
        self.env.cr.execute(query)
        if self.env.cr.dictfetchone():
            raise UserError(
                _(
                    "You defined a distribution with analytic account(s) belonging to a specific company but a model shared between companies or with a different company"
                )
            )

    @api.model
    def _get_distribution(self, vals):
        """Returns the combined distribution from all matching models based on the vals dict provided
        This method should be called to prefill analytic distribution field on several models"""
        applicable_models = self._get_applicable_models(
            {k: v for k, v in vals.items() if k != "related_root_plan_ids"}
        )

        res = {}
        applied_plans = vals.get(
            "related_root_plan_ids", self.env["account.analytic.plan"]
        )
        for model in applicable_models:
            # ignore model if it contains an account having a root plan that was already applied
            if not applied_plans & model.distribution_analytic_account_ids.root_plan_id:
                res |= model.analytic_distribution or {}
                applied_plans += model.distribution_analytic_account_ids.root_plan_id
        return res

    @api.model
    def _prepare_default_search_params(self):
        return {
            "company_id": False,
            "partner_id": False,
            "partner_tag_id": [],
        }

    @api.model
    def _get_applicable_models(self, vals):
        vals = self._prepare_default_search_params() | vals
        domain = Domain.AND(starmap(self._create_domain, vals.items()))
        return self._get_candidate_models().filtered_domain(domain)

    @api.model
    def _get_candidate_models(self):
        # a lookup runs once per distinct argument set -- one per invoice line
        # of a batch, typically -- and the models are few: every model the
        # user may read is fetched once per transaction and matched in Python
        per_env = CANDIDATE_MODELS(self.env)
        key = (self.env.uid, self.env.su, tuple(self.env.companies.ids))
        if key not in per_env:
            per_env[key] = self.search([]).ids
        return self.browse(per_env[key])

    def _create_domain(self, fname, value):
        if fname == "partner_tag_id":
            # Build a new list instead of `value += [False]`: the list belongs to
            # the caller's vals dict, and callers memoize on that dict.
            # `account.move.line._compute_analytic_distribution` keys a frozendict
            # on it, so mutating it after insertion made every later lookup compare
            # unequal -- the cache missed on every line and re-ran this search once
            # per invoice line. Repeated calls also kept appending (`[False, False,
            # ...]`).
            return [(fname, "in", [*value, False])]
        return [(fname, "in", [value, False])]
