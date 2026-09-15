import datetime
from contextlib import contextmanager
from math import copysign
from typing import NamedTuple

import psycopg.errors
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, formatLang
from odoo.tools.date_utils import end_of

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class LinearRecompute(NamedTuple):
    start_date: datetime.date
    residual: float
    lifetime_left: float


class AccountAsset(models.Model):
    _name = "account.asset"
    _description = "Asset/Revenue Recognition"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.analytic"]
    _check_company_auto = True

    count_depreciation_posted = fields.Integer(
        string="# Posted Depreciation Entries",
        compute="_compute_depreciation_entries_count",
    )
    count_increase = fields.Count(
        count_of="child_ids",
        string="# Gross Increases",
        help="Number of assets made to increase the value of the asset",
    )
    count_depreciation = fields.Count(
        count_of="depreciation_move_ids",
        string="# Depreciation Entries",
        help="Number of depreciation entries (posted or not)",
    )

    name = fields.Char(
        string="Asset Name",
        compute="_compute_name",
        store=True,
        readonly=False,
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    country_code = fields.Char(related="company_id.account_fiscal_country_id.code")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        store=True,
    )
    depreciation_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Running"),
            ("paused", "On Hold"),
            ("close", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        copy=False,
        readonly=True,
        help="When an asset is created, the status is 'Draft'.\n"
        "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n"
        "The 'On Hold' status can be set manually when you want to pause the depreciation of an asset for some time.\n"
        "You can manually close an asset when the depreciation is over.\n"
        "By cancelling an asset, all depreciation entries will be reversed",
    )
    active = fields.Boolean(default=True)

    depreciation_method = fields.Selection(
        selection=[
            ("linear", "Straight Line"),
            ("degressive", "Declining"),
            ("degressive_then_linear", "Declining then Straight Line"),
        ],
        default="linear",
        help="Choose the method to use to compute the amount of depreciation lines.\n"
        "  * Straight Line: Calculated on basis of: Gross Value / Duration\n"
        "  * Declining: Calculated on basis of: Residual Value * Declining Factor, with a minimum depreciation value equal to the straight line value once that exceeds the declining amount.\n"
        "  * Declining then Straight Line: Like Declining but with a minimum depreciation value equal to the straight line value.",
    )
    depreciation_duration = fields.Integer(
        string="Duration",
        default=5,
        help="The number of depreciations needed to depreciate your asset",
    )
    depreciation_period = fields.Selection(
        selection=[("1", "Months"), ("12", "Years")],
        string="Number of Months in a Period",
        default="12",
        help="The amount of time between two depreciations",
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
    date_prorata = fields.Date(
        compute="_compute_prorata_date",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
        required=True,
        help="Starting date of the period used in the prorata calculation of the first depreciation",
    )
    date_prorata_paused = fields.Date(compute="_compute_paused_prorata_date")
    account_asset_id = fields.Many2one(
        comodel_name="account.account",
        string="Fixed Asset Account",
        compute="_compute_account_asset_id",
        store=True,
        readonly=False,
        domain="[('account_type', '!=', 'off_balance')]",
        check_company=True,
        help="Account used to record the purchase of the asset at its original price.",
    )
    asset_group_id = fields.Many2one(
        comodel_name="account.asset.group",
        index=True,
        check_company=True,
        tracking=True,
    )
    account_depreciation_id = fields.Many2one(
        comodel_name="account.account",
        string="Depreciation Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]",
        check_company=True,
        help="Account used in the depreciation entries, to decrease the asset value.",
    )
    account_depreciation_expense_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]",
        check_company=True,
        help="Account used in the periodical entries, to record a part of the asset as expense.",
    )

    depreciation_journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_depreciation_journal_id",
        store=True,
        readonly=False,
        domain="[('type', '=', 'general')]",
        check_company=True,
    )

    value_original = fields.Monetary(
        compute="_compute_value",
        store=True,
        readonly=False,
    )
    value_book = fields.Monetary(
        compute="_compute_book_value",
        recursive=True,
        store=True,
        readonly=True,
        help="Sum of the depreciable value, the salvage value and the book value of all value increase items",
    )
    value_depreciable_residual = fields.Monetary(
        string="Depreciable Value",
        compute="_compute_value_residual",
    )
    value_salvage = fields.Monetary(
        string="Not Depreciable Value",
        compute="_compute_salvage_value",
        store=True,
        readonly=False,
        help="It is the amount you plan to have that you cannot depreciate.",
    )
    value_depreciable = fields.Monetary(compute="_compute_total_depreciable_value")
    value_increase = fields.Monetary(
        compute="_compute_gross_increase_value",
        compute_sudo=True,
    )
    value_non_deductible_tax = fields.Monetary(
        compute="_compute_value_non_deductible_tax",
        store=True,
        readonly=True,
    )
    value_purchase = fields.Monetary(compute="_compute_related_purchase_value")

    depreciation_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="depreciation_asset_id",
        string="Depreciation Lines",
    )
    original_move_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="asset_move_line_rel",
        column1="asset_id",
        column2="line_id",
        string="Journal Items",
        copy=False,
    )

    asset_properties = fields.Properties(
        definition="depreciation_profile_id.asset_properties_definition",
        string="Properties",
        copy=True,
    )

    date_acquisition = fields.Date(
        compute="_compute_acquisition_date",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
    )
    date_disposal = fields.Date(
        compute="_compute_disposal_date",
        store=True,
        readonly=False,
    )

    depreciation_profile_id = fields.Many2one(
        comodel_name="account.depreciation.profile",
        string="Depreciation Profile",
        change_default=True,
        index="btree_not_null",
        check_company=True,
    )
    account_type = fields.Selection(
        related="account_asset_id.account_type",
        string="Type of the account",
    )
    display_account_asset_id = fields.Boolean(
        compute="_compute_display_account_asset_id"
    )

    parent_id = fields.Many2one(
        comodel_name="account.asset",
        index=True,
        help="An asset has a parent when it is the result of gaining value",
    )
    child_ids = fields.One2many(
        comodel_name="account.asset",
        inverse_name="parent_id",
        help="The children are the gains in value of this asset",
    )

    value_depreciated_import = fields.Monetary(
        help="In case of an import from another software, you might need to use this field to have the right "
        "depreciation table report. This is the value that was already depreciated with entries not computed from this model"
    )

    depreciation_lifetime_days = fields.Float(
        compute="_compute_lifetime_days",
        recursive=True,
    )
    depreciation_paused_days = fields.Float(copy=False)

    value_gain_on_sale = fields.Monetary(
        string="Net gain on sale",
        copy=False,
        help="Net value of gain or loss on sale of an asset",
    )

    linked_assets_ids = fields.Many2many(
        comodel_name="account.asset",
        compute="_compute_linked_assets",
    )
    count_linked_asset = fields.Count(count_of="linked_assets_ids")
    warning_count_assets = fields.Boolean(compute="_compute_linked_assets")

    @api.depends("company_id")
    def _compute_depreciation_journal_id(self):
        AccountJournal = self.env["account.journal"]
        needs_default = self.filtered(
            lambda asset: asset.depreciation_journal_id.company_id != asset.company_id
        )
        default_per_company = {}
        for company in needs_default.company_id:
            default_per_company[company] = AccountJournal.search(  # noqa: E8507  one search per distinct company, not per asset
                [
                    *AccountJournal._check_company_domain(company),
                    ("type", "=", "general"),
                ],
                limit=1,
            )
        for asset in needs_default:
            asset.depreciation_journal_id = default_per_company[asset.company_id]

    @api.depends("value_salvage", "value_original")
    def _compute_total_depreciable_value(self):
        for asset in self:
            asset.value_depreciable = asset.value_original - asset.value_salvage

    @api.depends("value_original", "depreciation_profile_id")
    def _compute_salvage_value(self):
        for asset in self:
            pct = asset.depreciation_profile_id.value_salvage_pct
            if not float_is_zero(pct, precision_digits=6):
                asset.value_salvage = asset.value_original * pct

    @api.depends("depreciation_move_ids.date", "depreciation_state")
    def _compute_disposal_date(self):
        for asset in self:
            if asset.depreciation_state == "close":
                dates = asset.depreciation_move_ids.filtered(
                    lambda m: m.date and m.state != "cancel"
                ).mapped("date")
                asset.date_disposal = dates and max(dates)
            else:
                asset.date_disposal = False

    @api.depends(
        "original_move_line_ids",
        "original_move_line_ids.account_id",
        "value_non_deductible_tax",
    )
    def _compute_value(self):
        for record in self:
            if not record.original_move_line_ids:
                continue
            record.value_original = record.value_purchase
            if record.value_non_deductible_tax:
                record.value_original += record.value_non_deductible_tax

    @api.depends("original_move_line_ids")
    def _compute_display_account_asset_id(self):
        for record in self:
            record.display_account_asset_id = not record.original_move_line_ids

    @api.depends(
        "account_depreciation_id",
        "account_depreciation_expense_id",
        "original_move_line_ids",
    )
    def _compute_account_asset_id(self):
        for record in self:
            if record.original_move_line_ids:
                record.account_asset_id = record.original_move_line_ids.account_id[:1]
            elif not record.account_asset_id:
                record.account_asset_id = record.account_depreciation_id

    @api.depends("original_move_line_ids")
    def _compute_analytic_distribution(self):
        for asset in self:
            distribution_asset = {}
            amount_total = sum(asset.original_move_line_ids.mapped("balance"))
            if not float_is_zero(
                amount_total, precision_rounding=asset.currency_id.rounding
            ):
                for line in asset.original_move_line_ids._origin:
                    if line.analytic_distribution:
                        for account, distribution in line.analytic_distribution.items():
                            distribution_asset[account] = (
                                distribution_asset.get(account, 0)
                                + distribution * line.balance
                            )
                for account, distribution_amount in distribution_asset.items():
                    distribution_asset[account] = distribution_amount / amount_total
            asset.analytic_distribution = (
                distribution_asset or asset.analytic_distribution
            )

    @api.depends(
        "depreciation_duration",
        "depreciation_period",
        "depreciation_prorata",
        "date_prorata",
        "parent_id",
        "parent_id.depreciation_lifetime_days",
        "parent_id.date_prorata_paused",
    )
    def _compute_lifetime_days(self):
        for asset in self:
            if not asset.parent_id:
                if asset.depreciation_prorata == "daily_computation":
                    asset.depreciation_lifetime_days = (
                        asset.date_prorata
                        + relativedelta(
                            months=int(asset.depreciation_period)
                            * asset.depreciation_duration
                        )
                        - asset.date_prorata
                    ).days
                else:
                    asset.depreciation_lifetime_days = (
                        int(asset.depreciation_period)
                        * asset.depreciation_duration
                        * DAYS_PER_MONTH
                    )
            else:
                if asset.depreciation_prorata == "daily_computation":
                    parent_end_date = (
                        asset.parent_id.date_prorata_paused
                        + relativedelta(
                            days=int(asset.parent_id.depreciation_lifetime_days - 1)
                        )
                    )
                else:
                    parent_end_date = (
                        asset.parent_id.date_prorata_paused
                        + relativedelta(
                            months=int(
                                asset.parent_id.depreciation_lifetime_days
                                / DAYS_PER_MONTH
                            ),
                            days=int(
                                asset.parent_id.depreciation_lifetime_days
                                % DAYS_PER_MONTH
                            )
                            - 1,
                        )
                    )
                asset.depreciation_lifetime_days = asset._get_delta_days(
                    asset.date_prorata, parent_end_date
                )

    @api.depends("date_acquisition", "company_id", "depreciation_prorata")
    def _compute_prorata_date(self):
        for asset in self:
            if asset.depreciation_prorata == "none" and asset.date_acquisition:
                fiscalyear_date = asset._get_fiscalyear_dates(
                    asset.date_acquisition
                ).get("date_from")
                asset.date_prorata = fiscalyear_date
            else:
                asset.date_prorata = asset.date_acquisition

    @api.depends("date_prorata", "depreciation_prorata", "depreciation_paused_days")
    def _compute_paused_prorata_date(self):
        for asset in self:
            if asset.depreciation_prorata == "daily_computation":
                asset.date_prorata_paused = asset.date_prorata + relativedelta(
                    days=asset.depreciation_paused_days
                )
            else:
                asset.date_prorata_paused = asset.date_prorata + relativedelta(
                    months=int(asset.depreciation_paused_days / DAYS_PER_MONTH),
                    days=asset.depreciation_paused_days % DAYS_PER_MONTH,
                )

    @api.depends(
        "original_move_line_ids",
        "original_move_line_ids.balance",
        "original_move_line_ids.deductible_amount",
        "original_move_line_ids.quantity",
    )
    def _compute_related_purchase_value(self):
        for asset in self:
            value_purchase = sum(
                line.balance * line.deductible_amount / 100
                for line in asset.original_move_line_ids
            )
            if (
                asset.account_asset_id.multiple_assets_per_line
                and len(asset.original_move_line_ids) == 1
            ):
                value_purchase /= max(1, int(asset.original_move_line_ids.quantity))
            asset.value_purchase = value_purchase

    @api.depends("original_move_line_ids")
    def _compute_acquisition_date(self):
        for asset in self:
            asset.date_acquisition = asset.date_acquisition or min(
                [(aml.invoice_date or aml.date) for aml in asset.original_move_line_ids]
                + [fields.Date.today()]
            )

    @api.depends("original_move_line_ids")
    def _compute_name(self):
        for record in self:
            record.name = record.name or (
                (
                    record.original_move_line_ids
                    and record.original_move_line_ids[0].name
                )
                or ""
            )

    @api.depends(
        "value_original",
        "value_salvage",
        "value_depreciated_import",
        "depreciation_move_ids.state",
        "depreciation_move_ids.depreciation_value",
        "depreciation_move_ids.reversal_move_ids",
    )
    def _compute_value_residual(self):
        grouped_moves = self.env["account.move"]._read_group(
            domain=[
                ("depreciation_asset_id", "in", self.ids),
                ("state", "=", "posted"),
            ],
            groupby=["depreciation_asset_id"],
            aggregates=["depreciation_value:sum"],
        )
        depreciation_sum_by_asset = {asset.id: total for asset, total in grouped_moves}
        for record in self:
            asset_depreciation = depreciation_sum_by_asset.get(record.id, 0.0)
            record.value_depreciable_residual = (
                record.value_original
                - record.value_salvage
                - record.value_depreciated_import
                - asset_depreciation
            )

    @api.depends(
        "value_depreciable_residual",
        "value_salvage",
        "child_ids.value_book",
        "depreciation_state",
        "depreciation_move_ids.state",
    )
    def _compute_book_value(self):
        for record in self:
            record.value_book = (
                record.value_depreciable_residual
                + record.value_salvage
                + sum(record.child_ids.mapped("value_book"))
            )
            if record.depreciation_state == "close" and all(
                move.state == "posted" for move in record.depreciation_move_ids
            ):
                record.value_book -= record.value_salvage

    @api.depends("child_ids.value_original")
    def _compute_gross_increase_value(self):
        for record in self:
            record.value_increase = sum(record.child_ids.mapped("value_original"))

    @api.depends(
        "original_move_line_ids",
        "original_move_line_ids.non_deductible_tax_value",
        "original_move_line_ids.deductible_amount",
        "original_move_line_ids.quantity",
    )
    def _compute_value_non_deductible_tax(self):
        for record in self:
            record.value_non_deductible_tax = 0.0
            for line in record.original_move_line_ids:
                if line.non_deductible_tax_value:
                    account = line.account_id
                    auto_create_multi = (
                        account.create_asset != "no"
                        and account.multiple_assets_per_line
                    )
                    quantity = line.quantity if auto_create_multi else 1
                    converted_non_deductible_tax_value = line.currency_id._convert(
                        line.non_deductible_tax_value / quantity,
                        record.currency_id,
                        record.company_id,
                        line.date,
                    )
                    converted_non_deductible_tax_value *= line.deductible_amount / 100
                    record.value_non_deductible_tax += record.currency_id.round(
                        converted_non_deductible_tax_value
                    )

    @api.depends("depreciation_move_ids.state")
    def _compute_depreciation_entries_count(self):
        depreciation_per_asset = {
            group.id: count
            for group, count in self.env["account.move"]._read_group(
                domain=[
                    ("depreciation_asset_id", "in", self.ids),
                    ("state", "=", "posted"),
                ],
                groupby=["depreciation_asset_id"],
                aggregates=["__count"],
            )
        }
        for asset in self:
            asset.count_depreciation_posted = depreciation_per_asset.get(asset.id, 0)

    @api.depends("original_move_line_ids.capitalised_asset_ids")
    def _compute_linked_assets(self):
        for asset in self:
            asset.linked_assets_ids = (
                asset.original_move_line_ids.capitalised_asset_ids - asset
            )
            confirmed_assets = asset.linked_assets_ids.filtered(
                lambda x: x.depreciation_state == "open"
            )
            asset.warning_count_assets = len(confirmed_assets) > 0

    @api.onchange("value_original", "original_move_line_ids")
    def _display_original_value_warning(self):
        if self.original_move_line_ids:
            computed_original_value = (
                self.value_purchase + self.value_non_deductible_tax
            )
            if self.value_original != computed_original_value:
                warning = {
                    "title": _("Warning for the Original Value of %s", self.name),
                    "message": _(
                        "The amount you have entered (%(entered_amount)s) does not match the Related Purchase's value (%(purchase_value)s). "
                        "Please make sure this is what you want.",
                        entered_amount=formatLang(
                            self.env, self.value_original, currency_obj=self.currency_id
                        ),
                        purchase_value=formatLang(
                            self.env,
                            computed_original_value,
                            currency_obj=self.currency_id,
                        ),
                    ),
                }
                return {"warning": warning}
        return None

    @api.onchange("original_move_line_ids")
    def _onchange_original_move_line_ids(self):
        self.date_acquisition = False
        self._compute_acquisition_date()

    @api.onchange("account_asset_id")
    def _onchange_account_asset_id(self):
        self.account_depreciation_id = (
            self.account_depreciation_id or self.account_asset_id
        )

    @api.onchange("depreciation_profile_id")
    def _onchange_depreciation_profile_id(self):
        if self.depreciation_profile_id:
            defaults = self.depreciation_profile_id._get_asset_defaults()
            defaults.pop("analytic_distribution", None)
            self.update(defaults)
            self.analytic_distribution = (
                self.depreciation_profile_id.analytic_distribution
                or self.analytic_distribution
            )

    @api.onchange(
        "value_original",
        "value_salvage",
        "date_acquisition",
        "depreciation_method",
        "depreciation_factor",
        "depreciation_period",
        "depreciation_duration",
        "depreciation_prorata",
        "value_depreciated_import",
        "date_prorata",
    )
    def _onchange_consistent_board(self):
        self.write({"depreciation_move_ids": [Command.set([])]})

    @api.constrains("active", "depreciation_state")
    def _check_active(self):
        for record in self:
            if not record.active and record.depreciation_state != "close":
                raise UserError(_("You cannot archive a record that is not closed"))

    @api.constrains("depreciation_move_ids")
    def _check_depreciations(self):
        for asset in self:
            if (
                asset.depreciation_state == "open"
                and asset.depreciation_move_ids
                and not asset.currency_id.is_zero(
                    asset.depreciation_move_ids._sorted_by_date()[
                        -1
                    ].asset_remaining_value
                )
            ):
                raise UserError(
                    _("The remaining value on the last depreciation line must be 0")
                )

    @api.constrains("original_move_line_ids")
    def _check_single_source_account(self):
        for asset in self:
            if len(asset.original_move_line_ids.account_id) > 1:
                raise ValidationError(
                    _("All the lines should be from the same account")
                )

    @api.constrains("original_move_line_ids")
    def _check_related_purchase(self):
        for asset in self:
            if asset.original_move_line_ids and asset.value_purchase == 0:
                raise UserError(
                    _(
                        "You cannot create an asset from lines containing credit and debit on the account or with a null amount"
                    )
                )
            if asset.depreciation_state != "draft":
                raise UserError(
                    _(
                        "You cannot add or remove bills when the asset is already running or closed."
                    )
                )

    @api.ondelete(at_uninstall=True)
    def _unlink_if_model_or_draft(self):
        for asset in self:
            if asset.depreciation_state in ["open", "paused", "close"]:
                raise UserError(
                    _(
                        "You cannot delete a document that is in %s state.",
                        dict(
                            self._fields["depreciation_state"]._description_selection(
                                self.env
                            )
                        ).get(asset.depreciation_state),
                    )
                )

            posted_amount = len(
                asset.depreciation_move_ids.filtered(lambda x: x.state == "posted")
            )
            if posted_amount > 0:
                raise UserError(
                    _(
                        "You cannot delete an asset linked to posted entries."
                        "\nYou should either confirm the asset, then, sell or dispose of it,"
                        " or cancel the linked journal entries."
                    )
                )

    def unlink(self):
        bodies = {}
        orphaned_moves = self.env["account.move"]
        for asset in self:
            for line in asset.original_move_line_ids:
                if line.name:
                    body = _(
                        "A document linked to %(move_line_name)s has been deleted: %(link)s",
                        move_line_name=line.name,
                        link=asset._get_html_link(),
                    )
                else:
                    body = _(
                        "A document linked to this move has been deleted: %s",
                        asset._get_html_link(),
                    )
                bodies[line.move_id.id] = (
                    bodies[line.move_id.id] + Markup("<br>") + body
                    if line.move_id.id in bodies
                    else body
                )
                if not (line.move_id.capitalised_asset_ids - self):
                    orphaned_moves |= line.move_id
        if bodies:
            self.env["account.move"].browse(bodies)._message_log_batch(bodies=bodies)
        orphaned_moves.asset_move_type = False
        return super().unlink()

    def copy_data(self, default=None):
        vals_list = super().copy_data(default)
        for asset, vals in zip(self, vals_list, strict=True):
            vals["name"] = _("%s (copy)", asset.name)
            vals["account_asset_id"] = asset.account_asset_id.id
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            state = vals.get("depreciation_state")
            if state and state != "draft":
                raise UserError(
                    _(
                        "An asset is created in draft and confirmed afterwards; it cannot "
                        "be created directly in the %(state)s state.",
                        state=state,
                    )
                )
            if not vals.get("name") and not vals.get("original_move_line_ids"):
                raise UserError(_("An asset needs a name."))
            vals["depreciation_state"] = "draft"
        new_recs = super(
            AccountAsset, self.with_context(mail_create_nolog=True)
        ).create(vals_list)
        for record, vals in zip(new_recs, vals_list, strict=True):
            requested = vals.get("value_original")
            if requested is not None and record.currency_id.compare_amounts(
                record.value_original, requested
            ):
                record.value_original = requested
        return new_recs

    PROPAGATED_TO_MOVES = frozenset(
        {
            "analytic_distribution",
            "account_depreciation_id",
            "account_depreciation_expense_id",
            "depreciation_journal_id",
        }
    )

    def write(self, vals):
        propagated = self.PROPAGATED_TO_MOVES & vals.keys()
        if not propagated:
            return super().write(vals)
        previous_accounts = {
            asset.id: (
                asset.account_depreciation_id,
                asset.account_depreciation_expense_id,
            )
            for asset in self
        }
        result = super().write(vals)

        AccountMoveLine = self.env["account.move.line"]
        analytic_lines = AccountMoveLine
        depreciation_lines = AccountMoveLine
        expense_lines = AccountMoveLine
        rejournaled_moves = self.env["account.move"]
        for asset in self:
            lock_date = asset.company_id._get_user_fiscal_lock_date(
                asset.depreciation_journal_id
            )
            depreciation_account, expense_account = previous_accounts[asset.id]
            for move in asset.depreciation_move_ids:
                if move.state == "draft" and "analytic_distribution" in propagated:
                    analytic_lines |= move.line_ids
                if move.date <= lock_date:
                    continue
                if "account_depreciation_id" in propagated:
                    depreciation_lines |= move.line_ids.filtered(
                        lambda line: line.account_id == depreciation_account  # noqa: B023  the lambda runs inside this iteration
                    )
                if "account_depreciation_expense_id" in propagated:
                    expense_lines |= move.line_ids.filtered(
                        lambda line: line.account_id == expense_account  # noqa: B023  the lambda runs inside this iteration
                    )
                if "depreciation_journal_id" in propagated:
                    rejournaled_moves |= move

        if analytic_lines:
            analytic_lines.analytic_distribution = vals["analytic_distribution"]
        if depreciation_lines:
            depreciation_lines.account_id = vals["account_depreciation_id"]
        if expense_lines:
            expense_lines.account_id = vals["account_depreciation_expense_id"]
        if rejournaled_moves:
            rejournaled_moves.journal_id = vals["depreciation_journal_id"]
        return result

    def _get_linear_amount(
        self, days_before_period, days_until_period_end, value_depreciable
    ):

        amount_expected_previous_period = (
            value_depreciable * days_before_period / self.depreciation_lifetime_days
        )
        amount_after_expected = (
            value_depreciable * days_until_period_end / self.depreciation_lifetime_days
        )
        number_days_for_period = days_until_period_end - days_before_period
        amount_of_decrease_spread_over_period = [
            number_days_for_period
            * mv.depreciation_value
            / (
                self.depreciation_lifetime_days
                - self._get_delta_days(
                    self.date_prorata_paused, mv.asset_depreciation_beginning_date
                )
            )
            for mv in self.depreciation_move_ids.filtered(
                lambda mv: mv.asset_value_change
            )
        ]
        return self.currency_id.round(
            amount_after_expected
            - self.currency_id.round(amount_expected_previous_period)
            - sum(amount_of_decrease_spread_over_period)
        )

    def _compute_board_amount(
        self,
        residual_amount,
        period_start_date,
        period_end_date,
        days_left_to_depreciated,
        residual_declining,
        start_yearly_period=None,
        linear_recompute=None,
    ):

        def _get_max_between_linear_and_degressive(linear_amount):
            fiscalyear_dates = self._get_fiscalyear_dates(period_end_date)
            days_in_fiscalyear = self._get_delta_days(
                fiscalyear_dates["date_from"], fiscalyear_dates["date_to"]
            )

            degressive_total_value = residual_declining * (
                1
                - self.depreciation_factor
                * self._get_delta_days(start_yearly_period, period_end_date)
                / days_in_fiscalyear
            )
            degressive_amount = residual_amount - degressive_total_value
            return self._degressive_linear_amount(
                residual_amount, degressive_amount, linear_amount
            )

        if float_is_zero(self.depreciation_lifetime_days, 2) or float_is_zero(
            residual_amount, 2
        ):
            return 0, 0

        days_until_period_end = self._get_delta_days(
            self.date_prorata_paused, period_end_date
        )
        days_before_period = self._get_delta_days(
            self.date_prorata_paused, period_start_date + relativedelta(days=-1)
        )
        days_before_period = max(days_before_period, 0)
        number_days = days_until_period_end - days_before_period

        if self.depreciation_method == "linear":
            if (
                linear_recompute
                and float_compare(linear_recompute.lifetime_left, 0, 2) > 0
            ):
                computed_linear_amount = residual_amount - linear_recompute.residual * (
                    1
                    - self._get_delta_days(linear_recompute.start_date, period_end_date)
                    / linear_recompute.lifetime_left
                )
            else:
                computed_linear_amount = self._get_linear_amount(
                    days_before_period,
                    days_until_period_end,
                    self.value_depreciable,
                )
            amount = min(computed_linear_amount, residual_amount, key=abs)
        elif self.depreciation_method == "degressive":
            days_left_from_beginning_of_year = (
                self._get_delta_days(
                    start_yearly_period, period_start_date - relativedelta(days=1)
                )
                + days_left_to_depreciated
            )
            expected_remaining_value_with_linear = (
                residual_declining
                - residual_declining
                * self._get_delta_days(start_yearly_period, period_end_date)
                / days_left_from_beginning_of_year
            )
            linear_amount = residual_amount - expected_remaining_value_with_linear

            amount = _get_max_between_linear_and_degressive(linear_amount)
        elif self.depreciation_method == "degressive_then_linear":
            if not self.parent_id:
                linear_amount = self._get_linear_amount(
                    days_before_period,
                    days_until_period_end,
                    self.value_depreciable,
                )
            else:
                parent_moves = self.parent_id.depreciation_move_ids.filtered(
                    lambda mv: mv.date <= self.date_prorata
                )._sorted_by_date()
                parent_cumulative_depreciation = (
                    parent_moves[-1].asset_depreciated_value
                    if parent_moves
                    else self.parent_id.value_depreciated_import
                )
                parent_depreciable_value = (
                    parent_moves[-1].asset_remaining_value
                    if parent_moves
                    else self.parent_id.value_depreciable
                )
                if self.currency_id.is_zero(parent_depreciable_value):
                    linear_amount = self._get_linear_amount(
                        days_before_period,
                        days_until_period_end,
                        self.value_depreciable,
                    )
                else:
                    depreciable_value = self.value_depreciable * (
                        1 + parent_cumulative_depreciation / parent_depreciable_value
                    )
                    linear_amount = (
                        self._get_linear_amount(
                            days_before_period, days_until_period_end, depreciable_value
                        )
                        * self.depreciation_lifetime_days
                        / self.parent_id.depreciation_lifetime_days
                    )

            amount = _get_max_between_linear_and_degressive(linear_amount)
        else:
            raise UserError(
                _(
                    "The depreciation method %s has no board computation.",
                    self.depreciation_method,
                )
            )

        amount = (
            max(amount, 0)
            if self.currency_id.compare_amounts(residual_amount, 0) > 0
            else min(amount, 0)
        )
        amount = self._get_depreciation_amount_end_of_lifetime(
            residual_amount, amount, days_until_period_end
        )

        return number_days, self.currency_id.round(amount)

    def compute_depreciation_board(self, date=False):
        self.depreciation_move_ids.filtered(
            lambda mv: mv.state == "draft" and (mv.date >= date if date else True)
        ).unlink()

        new_depreciation_moves_data = []
        with self._shared_fiscalyear_dates():
            for asset in self:
                new_depreciation_moves_data.extend(asset._recompute_board(date))

        new_depreciation_moves = self.env["account.move"].create(
            new_depreciation_moves_data
        )
        new_depreciation_moves_to_post = new_depreciation_moves.filtered(
            lambda move: move.depreciation_asset_id.depreciation_state == "open"
        )
        new_depreciation_moves_to_post._post()

    def _recompute_board(self, start_depreciation_date=False):
        self.check_singleton()
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == "posted" and not mv.asset_value_change
        )._sorted_by_date()

        imported_amount = self.value_depreciated_import
        residual_amount = self.value_depreciable_residual - sum(
            self.depreciation_move_ids.filtered(lambda mv: mv.state == "draft").mapped(
                "depreciation_value"
            )
        )
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount
        residual_declining = residual_amount
        start_depreciation_date = start_yearly_period = (
            start_depreciation_date or self.date_prorata_paused
        )

        last_day_asset = self._get_last_day_asset()
        final_depreciation_date = self._get_end_period_date(last_day_asset)
        linear_recompute = LinearRecompute(
            start_date=start_depreciation_date,
            residual=residual_amount,
            lifetime_left=self._get_delta_days(start_depreciation_date, last_day_asset),
        )

        depreciation_move_values = []
        if not float_is_zero(
            self.value_depreciable_residual,
            precision_rounding=self.currency_id.rounding,
        ):
            while (
                not self.currency_id.is_zero(residual_amount)
                and start_depreciation_date < final_depreciation_date
            ):
                period_end_depreciation_date = self._get_end_period_date(
                    start_depreciation_date
                )
                period_end_fiscalyear_date = self._get_fiscalyear_dates(
                    period_end_depreciation_date
                ).get("date_to")
                lifetime_left = self._get_delta_days(
                    start_depreciation_date, last_day_asset
                )

                days, amount = self._compute_board_amount(
                    residual_amount,
                    start_depreciation_date,
                    period_end_depreciation_date,
                    lifetime_left,
                    residual_declining,
                    start_yearly_period,
                    linear_recompute,
                )
                residual_amount -= amount

                if not posted_depreciation_move_ids:
                    if abs(imported_amount) <= abs(amount):
                        amount -= imported_amount
                        imported_amount = 0
                    else:
                        imported_amount -= amount
                        amount = 0

                if (
                    self.depreciation_method == "degressive_then_linear"
                    and final_depreciation_date < period_end_depreciation_date
                ):
                    period_end_depreciation_date = final_depreciation_date

                if not float_is_zero(
                    amount, precision_rounding=self.currency_id.rounding
                ):
                    depreciation_move_values.append(
                        self.env["account.move"]._prepare_move_for_asset_depreciation(
                            {
                                "amount": amount,
                                "asset_id": self,
                                "depreciation_beginning_date": start_depreciation_date,
                                "date": period_end_depreciation_date,
                                "asset_number_days": days,
                            }
                        )
                    )

                if period_end_depreciation_date == period_end_fiscalyear_date:
                    start_yearly_period = self._get_fiscalyear_dates(
                        period_end_depreciation_date + relativedelta(days=1)
                    ).get("date_from")
                    residual_declining = residual_amount

                start_depreciation_date = period_end_depreciation_date + relativedelta(
                    days=1
                )

        return depreciation_move_values

    FISCALYEAR_MEMO_KEY = "account_depreciation.fiscalyear_dates"

    @contextmanager
    def _shared_fiscalyear_dates(self):
        cache = self.env.cr.cache
        if self.FISCALYEAR_MEMO_KEY in cache:
            yield
            return
        cache[self.FISCALYEAR_MEMO_KEY] = {}
        try:
            yield
        finally:
            cache.pop(self.FISCALYEAR_MEMO_KEY, None)

    def _get_fiscalyear_dates(self, date):
        self.check_singleton()
        memo = self.env.cr.cache.get(self.FISCALYEAR_MEMO_KEY)
        if memo is None:
            return self.company_id.compute_fiscalyear_dates(date)
        key = (self.company_id.id, date)
        if key not in memo:
            memo[key] = self.company_id.compute_fiscalyear_dates(date)
        return dict(memo[key])

    def _get_end_period_date(self, start_depreciation_date):
        self.check_singleton()
        fiscalyear_date = self._get_fiscalyear_dates(start_depreciation_date).get(
            "date_to"
        )
        period_end_depreciation_date = (
            fiscalyear_date
            if start_depreciation_date <= fiscalyear_date
            else fiscalyear_date + relativedelta(years=1)
        )

        if self.depreciation_period == "1":
            max_day_in_month = end_of(
                datetime.date(
                    start_depreciation_date.year, start_depreciation_date.month, 1
                ),
                "month",
            ).day
            period_end_depreciation_date = min(
                start_depreciation_date.replace(day=max_day_in_month),
                period_end_depreciation_date,
            )
        return period_end_depreciation_date

    def _get_delta_days(self, start_date, end_date):
        self.check_singleton()
        if self.depreciation_prorata == "daily_computation":
            return (end_date - start_date).days + 1
        else:
            start_date_days_month = end_of(start_date, "month").day
            start_prorata = (
                start_date_days_month - start_date.day + 1
            ) / start_date_days_month
            end_prorata = end_date.day / end_of(end_date, "month").day
            return sum(
                (
                    start_prorata * DAYS_PER_MONTH,
                    end_prorata * DAYS_PER_MONTH,
                    (end_date.year - start_date.year) * DAYS_PER_YEAR,
                    (end_date.month - start_date.month - 1) * DAYS_PER_MONTH,
                )
            )

    def _get_last_day_asset(self):
        this = self.parent_id or self
        return this.date_prorata_paused + relativedelta(
            months=int(this.depreciation_period) * this.depreciation_duration, days=-1
        )

    def action_view_linked_assets(self):
        return self.linked_assets_ids.open_asset(["list", "form"])

    def action_asset_modify(self):
        self.check_singleton()
        new_wizard = self.env["asset.modify"].create(
            {
                "asset_id": self.id,
                "modify_action": "resume"
                if self.env.context.get("resume_after_pause")
                else "dispose",
            }
        )
        return {
            "name": _("Modify Asset"),
            "view_mode": "form",
            "res_model": "asset.modify",
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": new_wizard.id,
            "context": self.env.context,
        }

    def action_save_profile(self):
        self.check_singleton()
        profile = self.env["account.depreciation.profile"].create(
            self._get_profile_values()
        )
        self.depreciation_profile_id = profile
        return {
            "name": _("Depreciation Profile"),
            "type": "ir.actions.act_window",
            "res_model": "account.depreciation.profile",
            "res_id": profile.id,
            "views": [(False, "form")],
        }

    def open_entries(self):
        return {
            "name": _("Journal Entries"),
            "view_mode": "list,form",
            "res_model": "account.move",
            "search_view_id": [
                self.env.ref("account.view_account_move_filter").id,
                "search",
            ],
            "views": [
                (self.env.ref("account.view_move_tree").id, "list"),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.depreciation_move_ids.ids)],
            "context": dict(self.env.context, create=False),
        }

    def open_related_entries(self):
        return {
            "name": _("Journal Items"),
            "view_mode": "list,form",
            "res_model": "account.move.line",
            "view_id": False,
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.original_move_line_ids.ids)],
        }

    def open_increase(self):
        result = {
            "name": _("Gross Increase"),
            "view_mode": "list,form",
            "res_model": "account.asset",
            "context": {**self.env.context, "create": False},
            "view_id": False,
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.child_ids.ids)],
            "views": [(False, "list"), (False, "form")],
        }
        if len(self.child_ids) == 1:
            result["views"] = [(False, "form")]
            result["res_id"] = self.child_ids.id
        return result

    def open_parent_id(self):
        return {
            "name": _("Parent Asset"),
            "view_mode": "form",
            "res_model": "account.asset",
            "type": "ir.actions.act_window",
            "res_id": self.parent_id.id,
            "views": [(False, "form")],
        }

    CREATION_TRACKED_FNAMES = (
        "depreciation_method",
        "depreciation_duration",
        "depreciation_period",
        "depreciation_factor",
        "value_salvage",
        "original_move_line_ids",
    )

    def _log_asset_created(self):
        tracked_fnames = list(self.CREATION_TRACKED_FNAMES)
        ref_tracked_fields = self.fields_get(tracked_fnames)
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.depreciation_method == "linear":
                del tracked_fields["depreciation_factor"]
            _dummy, tracking_value_ids = asset._mail_track(
                tracked_fields, dict.fromkeys(tracked_fnames)
            )
            asset.message_post(
                body=_("Asset created"), tracking_value_ids=tracking_value_ids
            )
            move_body = _("An asset has been created for this move: %s") % (
                asset._get_html_link()
            )
            for move_id in asset.original_move_line_ids.mapped("move_id"):
                move_id.message_post(body=move_body)

    def validate(self):
        self.write({"depreciation_state": "open"})
        self._log_asset_created()
        try:
            with self.env.cr.savepoint():
                boardless = self.filtered(lambda asset: not asset.depreciation_move_ids)
                if boardless:
                    boardless.compute_depreciation_board()
                self._check_depreciations()
                unposted = self.depreciation_move_ids.filtered(
                    lambda move: move.state != "posted"
                )
                if unposted:
                    unposted._post()
        except psycopg.errors.CheckViolation:
            raise ValidationError(
                _(
                    "At least one asset (%s) couldn't be set as running because it lacks any required information",
                    ", ".join(self.mapped("name")),
                )
            ) from None

        for asset in self.filtered(
            lambda asset: asset.account_asset_id.create_asset == "no"
        ):
            asset._post_non_deductible_tax_value()

    def set_to_close(self, invoice_line_ids, date=None, message=None):
        self.check_singleton()
        date_disposal = date or fields.Date.today()
        if date_disposal <= self.company_id._get_user_fiscal_lock_date(
            self.depreciation_journal_id
        ):
            raise UserError(_("You cannot dispose of an asset before the lock date."))
        if invoice_line_ids and self.child_ids.filtered(
            lambda a: (
                a.depreciation_state in ("draft", "open")
                or a.value_depreciable_residual > 0
            )
        ):
            raise UserError(
                _(
                    "You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."
                )
            )
        full_asset = (self + self.child_ids).filtered(
            lambda asset: asset.depreciation_state not in ("close", "cancelled")
        )
        full_asset.depreciation_state = "close"
        move_ids = full_asset._get_disposal_moves(
            [
                invoice_line_ids if asset == self else self.env["account.move.line"]
                for asset in full_asset
            ],
            date_disposal,
        )
        if invoice_line_ids:
            invoice_moves = invoice_line_ids.move_id
            invoice_links = Markup(", ").join(
                move._get_html_link() for move in invoice_moves
            )
            asset_body = self.env._(
                "Asset sold. %(message)s See %(invoice_links)s",
                message=message or "",
                invoice_links=invoice_links,
            )
            invoice_body = self.env._("Asset sold: %s", self._get_html_link())
            invoice_moves._message_log_batch(
                bodies={invoice.id: invoice_body for invoice in invoice_moves}
            )
        else:
            asset_body = self.env._(
                "Asset disposed. %(message)s",
                message=message or "",
            )

        full_asset._message_log_batch(
            bodies={asset.id: asset_body for asset in full_asset}
        )

        selling_price = abs(
            sum(invoice_line.balance for invoice_line in invoice_line_ids)
        )
        self.value_gain_on_sale = self.currency_id.round(
            selling_price - self.value_book
        )

        if move_ids:
            name = _("Disposal Move")
            view_mode = "form"
            if len(move_ids) > 1:
                name = _("Disposal Moves")
                view_mode = "list,form"
            return {
                "name": name,
                "view_mode": view_mode,
                "res_model": "account.move",
                "type": "ir.actions.act_window",
                "target": "current",
                "res_id": move_ids[0],
                "domain": [("id", "in", move_ids)],
            }
        return None

    def set_to_cancelled(self):
        for asset in self:
            posted_moves = asset.depreciation_move_ids.filtered(
                lambda m: m._is_effective_depreciation()
            )
            if posted_moves:
                depreciation_change = sum(
                    posted_moves.line_ids.mapped(
                        lambda l: (
                            l.debit
                            if l.account_id == asset.account_depreciation_expense_id  # noqa: B023  the lambda runs inside this iteration
                            else 0.0
                        )
                    )
                )
                acc_depreciation_change = sum(
                    posted_moves.line_ids.mapped(
                        lambda l: (
                            l.credit
                            if l.account_id == asset.account_depreciation_id  # noqa: B023  the lambda runs inside this iteration
                            else 0.0
                        )
                    )
                )
                entries = Markup("<br>").join(
                    posted_moves._sorted_by_date().mapped(
                        lambda m: (
                            f"{m.ref} - {m.date} - "
                            f"{formatLang(self.env, m.depreciation_value, currency_obj=m.currency_id)} - "
                            f"{m.name}"
                        )
                    )
                )
                asset._cancel_future_moves(datetime.date.min)
                msg = (
                    _("Asset Cancelled")
                    + Markup("<br>")
                    + _(
                        "The account %(exp_acc)s has been credited by %(exp_delta)s, "
                        "while the account %(dep_acc)s has been debited by %(dep_delta)s. "
                        "This corresponds to %(move_count)s cancelled %(word)s:",
                        exp_acc=asset.account_depreciation_expense_id.display_name,
                        exp_delta=formatLang(
                            self.env,
                            depreciation_change,
                            currency_obj=asset.currency_id,
                        ),
                        dep_acc=asset.account_depreciation_id.display_name,
                        dep_delta=formatLang(
                            self.env,
                            acc_depreciation_change,
                            currency_obj=asset.currency_id,
                        ),
                        move_count=len(posted_moves),
                        word=_("entries") if len(posted_moves) > 1 else _("entry"),
                    )
                    + Markup("<br>")
                    + entries
                )
                asset._message_log(body=msg)
            else:
                asset._message_log(body=_("Asset Cancelled"))
            asset.depreciation_move_ids.filtered(
                lambda m: m.state == "draft"
            ).with_context(force_delete=True).unlink()
            asset.depreciation_paused_days = 0
            asset.write({"depreciation_state": "cancelled"})

    def set_to_draft(self):
        self.write({"depreciation_state": "draft"})

    def set_to_running(self):
        self.check_singleton()
        if self.depreciation_move_ids and not self.currency_id.is_zero(
            self.depreciation_move_ids._sorted_by_date()[-1].asset_remaining_value
        ):
            self.env["asset.modify"].create(
                {"asset_id": self.id, "name": _("Reset to running")}
            ).modify()
        self.write({"depreciation_state": "open", "value_gain_on_sale": 0})

    def resume_after_pause(self):
        self.check_singleton()
        return self.with_context(resume_after_pause=True).action_asset_modify()

    def pause(self, pause_date, message=None):
        self.check_singleton()
        self._create_move_before_date(pause_date)
        self.write({"depreciation_state": "paused"})
        self.message_post(body=_("Asset paused. %s", message or ""))

    def open_asset(self, view_mode):
        if len(self) == 1:
            view_mode = ["form"]
        views = [v for v in [(False, "list"), (False, "form")] if v[1] in view_mode]
        ctx = dict(self.env.context)
        ctx.pop("default_move_type", None)
        return {
            "name": _("Asset"),
            "view_mode": ",".join(view_mode),
            "type": "ir.actions.act_window",
            "res_id": self.id if len(self) == 1 else False,
            "res_model": "account.asset",
            "views": views,
            "domain": [("id", "in", self.ids)],
            "context": ctx,
        }

    def _add_depreciation_line(
        self, amount, beginning_depreciation_date, depreciation_date, days_depreciated
    ):
        self.check_singleton()
        AccountMove = self.env["account.move"]

        return AccountMove.create(
            AccountMove._prepare_move_for_asset_depreciation(
                {
                    "amount": amount,
                    "asset_id": self,
                    "depreciation_beginning_date": beginning_depreciation_date,
                    "date": depreciation_date,
                    "asset_number_days": days_depreciated,
                }
            )
        )

    def _get_profile_values(self):
        self.check_singleton()
        return {
            "name": self.name,
            "company_id": self.company_id.id,
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

    def _post_non_deductible_tax_value(self):
        if self.value_non_deductible_tax:
            currency = self.env.company.currency_id
            msg = _(
                "A non deductible tax value of %(tax_value)s was added to %(name)s's initial value of %(purchase_value)s",
                tax_value=formatLang(
                    self.env, self.value_non_deductible_tax, currency_obj=currency
                ),
                name=self.name,
                purchase_value=formatLang(
                    self.env, self.value_purchase, currency_obj=currency
                ),
            )
            self.message_post(body=msg)

    def _create_move_before_date(self, date):
        all_move_dates_before_date = self.depreciation_move_ids.filtered(
            lambda x: x.date <= date and x._is_effective_depreciation()
        ).mapped("date")

        beginning_fiscal_year = (
            self._get_fiscalyear_dates(date).get("date_from")
            if self.depreciation_method != "linear"
            else False
        )
        if beginning_fiscal_year:
            beginning_fiscal_year = max(beginning_fiscal_year, self.date_prorata_paused)
        first_fiscalyear_move = self.env["account.move"]
        if all_move_dates_before_date:
            last_move_date_not_reversed = max(all_move_dates_before_date)
            future_moves_beginning_date = self.depreciation_move_ids.filtered(
                lambda m: (
                    m.date > last_move_date_not_reversed
                    and (m._is_effective_depreciation() or m.state == "draft")
                )
            ).mapped("asset_depreciation_beginning_date")
            beginning_depreciation_date = (
                min(future_moves_beginning_date)
                if future_moves_beginning_date
                else self.date_prorata_paused
            )

            if self.depreciation_method != "linear":
                first_moves = self.depreciation_move_ids.filtered(
                    lambda m: (
                        m.asset_depreciation_beginning_date >= beginning_fiscal_year
                        and (m._is_effective_depreciation() or m.state == "draft")
                    )
                ).sorted(lambda m: (m.asset_depreciation_beginning_date, m.id))
                first_fiscalyear_move = next(iter(first_moves), first_fiscalyear_move)
        else:
            beginning_depreciation_date = self.date_prorata_paused

        residual_declining = (
            first_fiscalyear_move.asset_remaining_value
            + first_fiscalyear_move.depreciation_value
        )
        self._cancel_future_moves(date)

        imported_amount = (
            self.value_depreciated_import if not all_move_dates_before_date else 0
        )
        value_depreciable_residual = (
            self.value_depreciable_residual + self.value_depreciated_import
            if not all_move_dates_before_date
            else self.value_depreciable_residual
        )
        residual_declining = residual_declining or value_depreciable_residual

        last_day_asset = self._get_last_day_asset()
        lifetime_left = self._get_delta_days(
            beginning_depreciation_date, last_day_asset
        )
        days_depreciated, amount = self._compute_board_amount(
            self.value_depreciable_residual,
            beginning_depreciation_date,
            date,
            lifetime_left,
            residual_declining,
            beginning_fiscal_year,
            LinearRecompute(
                start_date=beginning_depreciation_date,
                residual=value_depreciable_residual,
                lifetime_left=lifetime_left,
            ),
        )

        if abs(imported_amount) <= abs(amount):
            amount -= imported_amount
        if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
            new_line = self._add_depreciation_line(
                amount, beginning_depreciation_date, date, days_depreciated
            )
            new_line._post()

    def _cancel_future_moves(self, date):
        for asset in self:
            obsolete_moves = asset.depreciation_move_ids.filtered(
                lambda m: (
                    m.state == "draft"
                    or (m._is_effective_depreciation() and m.date > date)
                )
            )
            obsolete_moves._unlink_or_reverse()

    def _get_disposal_moves(self, invoice_lines_list, date_disposal):

        def get_line(name, asset, amount, account, is_sale):
            return (
                0,
                0,
                {
                    "name": name,
                    "account_id": account.id,
                    "balance": -amount,
                    "analytic_distribution": analytic_distribution,
                    "currency_id": asset.currency_id.id,
                    "amount_currency": -asset.company_id.currency_id._convert(
                        from_amount=amount,
                        to_currency=asset.currency_id,
                        company=asset.company_id,
                        date=date_disposal,
                    ),
                    "is_storno": asset.company_id.account_storno
                    and is_sale
                    and (
                        account
                        not in (
                            asset.company_id.gain_account_id,
                            asset.company_id.loss_account_id,
                        )
                    ),
                },
            )

        move_ids = []
        for asset, invoice_line_ids in zip(self, invoice_lines_list, strict=True):
            asset._create_move_before_date(date_disposal)

            analytic_distribution = asset.analytic_distribution

            dict_invoice = {}
            invoice_amount = 0

            initial_amount = asset.value_original
            initial_account = (
                asset.original_move_line_ids.account_id
                if len(asset.original_move_line_ids.account_id) == 1
                else asset.account_asset_id
            )

            all_lines_before_disposal = asset.depreciation_move_ids.filtered(
                lambda x: x.date <= date_disposal
            )
            depreciated_amount = asset.currency_id.round(
                copysign(
                    sum(all_lines_before_disposal.mapped("depreciation_value"))
                    + asset.value_depreciated_import,
                    -initial_amount,
                )
            )
            depreciation_account = asset.account_depreciation_id
            for invoice_line in invoice_line_ids:
                dict_invoice[invoice_line.account_id] = copysign(
                    invoice_line.balance, -initial_amount
                ) + dict_invoice.get(invoice_line.account_id, 0)
                invoice_amount += copysign(invoice_line.balance, -initial_amount)
            list_accounts = [
                (amount, account) for account, amount in dict_invoice.items()
            ]
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = (
                asset.company_id.gain_account_id
                if difference > 0
                else asset.company_id.loss_account_id
            )
            line_datas = (
                [
                    (initial_amount, initial_account),
                    (depreciated_amount, depreciation_account),
                ]
                + list_accounts
                + [(difference, difference_account)]
            )
            name = (
                _("%(asset)s: Disposal", asset=asset.name)
                if not invoice_line_ids
                else _("%(asset)s: Sale", asset=asset.name)
            )
            vals = {
                "depreciation_asset_id": asset.id,
                "ref": name,
                "asset_depreciation_beginning_date": date_disposal,
                "date": date_disposal,
                "journal_id": asset.depreciation_journal_id.id,
                "move_type": "entry",
                "asset_move_type": "disposal" if not invoice_line_ids else "sale",
                "line_ids": [
                    get_line(name, asset, amount, account, invoice_line_ids)
                    for amount, account in line_datas
                    if account
                ],
            }
            move_ids += self.env["account.move"].create(vals).ids

        return move_ids

    def _degressive_linear_amount(
        self, residual_amount, degressive_amount, linear_amount
    ):
        if self.currency_id.compare_amounts(residual_amount, 0) > 0:
            return max(degressive_amount, linear_amount)
        else:
            return min(degressive_amount, linear_amount)

    def _get_depreciation_amount_end_of_lifetime(
        self, residual_amount, amount, days_until_period_end
    ):
        if (
            abs(residual_amount) < abs(amount)
            or days_until_period_end >= self.depreciation_lifetime_days
        ):
            amount = residual_amount
        return amount

    def _get_own_book_value(self, date=None):
        self.check_singleton()
        return (
            self._get_residual_value_at_date(date)
            if date
            else self.value_depreciable_residual
        ) + self.value_salvage

    def _get_residual_value_at_date(self, date):
        current_and_previous_depreciation = self.depreciation_move_ids.filtered(
            lambda mv: (
                mv.asset_depreciation_beginning_date < date and not mv.reversed_entry_id
            )
        ).sorted("asset_depreciation_beginning_date", reverse=True)
        undepreciated_value = (
            self.value_original - self.value_salvage - self.value_depreciated_import
        )
        if not current_and_previous_depreciation:
            return self._clamp_to_original_sign(undepreciated_value)

        if len(current_and_previous_depreciation) > 1:
            previous_value_residual = current_and_previous_depreciation[
                1
            ].asset_remaining_value
        else:
            previous_value_residual = undepreciated_value

        cur_depr_end_date = self._get_end_period_date(date)
        current_depreciation = current_and_previous_depreciation[0]
        cur_depr_beg_date = current_depreciation.asset_depreciation_beginning_date

        rate = self._get_delta_days(cur_depr_beg_date, date) / self._get_delta_days(
            cur_depr_beg_date, cur_depr_end_date
        )
        lost_value_at_date = (
            previous_value_residual - current_depreciation.asset_remaining_value
        ) * rate
        residual_value_at_date = self.currency_id.round(
            previous_value_residual - lost_value_at_date
        )
        return self._clamp_to_original_sign(residual_value_at_date)

    def _clamp_to_original_sign(self, value):
        self.check_singleton()
        if self.currency_id.compare_amounts(self.value_original, 0) > 0:
            return max(value, 0)
        return min(value, 0)
