import re

from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountAnalyticApplicability(models.Model):
    _inherit = "account.analytic.applicability"
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ("invoice", "Invoice"),
            ("bill", "Vendor Bill"),
        ],
        ondelete={
            "invoice": "cascade",
            "bill": "cascade",
        },
    )
    account_prefix = fields.Char(
        string="Financial Accounts Prefixes",
        help="Prefix that defines which accounts from the financial accounting this applicability should apply on.",
    )
    product_categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
    )
    display_account_prefix = fields.Boolean(
        compute="_compute_display_account_prefix",
        help="Defines if the field account prefix should be displayed",
    )
    account_prefix_placeholder = fields.Char(
        compute="_compute_account_prefix_placeholder"
    )

    @api.depends("account_prefix", "business_domain")
    @_debug.perf.timed
    def _compute_account_prefix_placeholder(self):
        account_expense = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.env.company),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        account_income = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.env.company),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        _debug.logic(
            "placeholder_accounts_found",
            expense=account_expense,
            income=account_income,
            applicabilities=len(self),
        )

        for applicability in self:
            if applicability.business_domain == "bill":
                account = account_expense
                account_prefixes = "60, 61, 62"
            else:
                account = account_income
                account_prefixes = "40, 41, 42"

            if account and account.code:
                prefix_base = account.code[:2]
                try:
                    prefix_num = int(prefix_base)
                    account_prefixes = (
                        f"{prefix_num}, {prefix_num + 1}, {prefix_num + 2}"
                    )
                except ValueError:
                    pass

            _debug.logic(
                "placeholder_prefixes_chosen",
                domain=applicability.business_domain,
                account=account,
                prefixes=account_prefixes,
            )
            applicability.account_prefix_placeholder = _(
                "e.g. %(prefix)s", prefix=account_prefixes
            )

    def _get_score(self, **kwargs):
        score = super()._get_score(**kwargs)
        if score == -1:
            return -1
        product = self.env["product.product"].browse(kwargs.get("product"))
        account = self.env["account.account"].browse(kwargs.get("account"))
        if self.account_prefix:
            account_prefixes = tuple(
                prefix
                for prefix in re.split(r"[,;]", self.account_prefix.replace(" ", ""))
                if prefix
            )
            if account.code and account.code.startswith(account_prefixes):
                score += 1
            else:
                _debug.logic(
                    "applicability_rejected",
                    applicability=self,
                    reason="account_prefix",
                    account=account,
                )
                return -1
        if self.product_categ_id:
            if product and product.categ_id == self.product_categ_id:
                score += 1
            else:
                _debug.logic(
                    "applicability_rejected",
                    applicability=self,
                    reason="product_category",
                    product=product,
                )
                return -1
        return score

    @api.depends("business_domain")
    def _compute_display_account_prefix(self):
        for applicability in self:
            applicability.display_account_prefix = applicability.business_domain in (
                "general",
                "invoice",
                "bill",
            )
