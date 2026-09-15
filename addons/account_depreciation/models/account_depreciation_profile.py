from odoo import api, fields, models


class AccountDepreciationProfile(models.Model):
    _name = "account.depreciation.profile"
    _description = "Depreciation Profile"
    _inherit = ["mixin.mail.thread", "mixin.analytic"]
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(
        translate=True,
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    depreciation_method = fields.Selection(
        selection=[
            ("linear", "Straight Line"),
            ("degressive", "Declining"),
            ("degressive_then_linear", "Declining then Straight Line"),
        ],
        string="Method",
        default="linear",
        required=True,
        tracking=True,
    )
    depreciation_duration = fields.Integer(
        string="Duration",
        default=5,
        tracking=True,
        help="The number of depreciations needed to depreciate an asset",
    )
    depreciation_period = fields.Selection(
        selection=[("1", "Months"), ("12", "Years")],
        string="Number of Months in a Period",
        default="12",
        required=True,
        tracking=True,
    )
    depreciation_factor = fields.Float(
        string="Declining Factor",
        default=0.3,
    )
    depreciation_prorata = fields.Selection(
        selection=[
            ("none", "No Prorata"),
            ("constant_periods", "Constant Periods"),
            ("daily_computation", "Based on days per period"),
        ],
        string="Computation",
        default="constant_periods",
        required=True,
    )
    value_salvage_pct = fields.Float(
        string="Not Depreciable Value Percent",
        help="The share of an asset's original value that is never depreciated.",
    )

    account_asset_id = fields.Many2one(
        comodel_name="account.account",
        string="Fixed Asset Account",
        domain="[('account_type', '!=', 'off_balance')]",
        check_company=True,
        tracking=True,
        help="Account used to record the purchase of the asset at its original price.",
    )
    account_depreciation_id = fields.Many2one(
        comodel_name="account.account",
        string="Depreciation Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]",
        check_company=True,
        tracking=True,
        help="Account used in the depreciation entries, to decrease the asset value.",
    )
    account_depreciation_expense_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]",
        check_company=True,
        tracking=True,
        help="Account used in the periodical entries, to record a part of the asset as expense.",
    )
    depreciation_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        compute="_compute_depreciation_journal_id",
        store=True,
        readonly=False,
        domain="[('type', '=', 'general')]",
        check_company=True,
    )

    kind_id = fields.Many2one(
        comodel_name="resource.asset.kind",
        string="Asset Kind",
        help="The kind given to an asset this profile creates. Without one, the asset is a Fixed Asset.",
    )
    asset_ids = fields.One2many(
        comodel_name="resource.asset",
        inverse_name="depreciation_profile_id",
        string="Assets",
    )
    count_asset = fields.Count(count_of="asset_ids")

    @api.depends("company_id")
    def _compute_depreciation_journal_id(self):
        AccountJournal = self.env["account.journal"]
        needs_default = self.filtered(
            lambda profile: (
                profile.depreciation_journal_id.company_id != profile.company_id
            )
        )
        for company in needs_default.company_id:
            journal = AccountJournal.search(  # noqa: E8507  one search per distinct company, not per profile
                [
                    *AccountJournal._check_company_domain(company),
                    ("type", "=", "general"),
                ],
                limit=1,
            )
            needs_default.filtered(
                lambda profile: profile.company_id == company  # noqa: B023  the lambda runs inside this iteration
            ).depreciation_journal_id = journal

    def _get_asset_defaults(self):
        self.check_singleton()
        return {
            "depreciation_method": self.depreciation_method,
            "depreciation_duration": self.depreciation_duration,
            "depreciation_period": self.depreciation_period,
            "depreciation_factor": self.depreciation_factor,
            "depreciation_prorata": self.depreciation_prorata,
            "analytic_distribution": self.analytic_distribution,
            "account_asset_id": self.account_asset_id.id,
            "account_depreciation_id": self.account_depreciation_id.id,
            "account_depreciation_expense_id": self.account_depreciation_expense_id.id,
            "depreciation_journal_id": self.depreciation_journal_id.id,
        }

    def action_view_assets(self):
        self.check_singleton()
        return self.asset_ids.open_asset(["list", "form"])
