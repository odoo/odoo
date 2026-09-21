from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_compare
from odoo.tools.misc import formatLang

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    depreciation_board_id = fields.Many2one(
        comodel_name="account.depreciation.board",
        index=True,
        copy=False,
        domain="[('company_id', '=', company_id)]",
        ondelete="cascade",
    )
    depreciation_asset_id = fields.Many2one(
        related="depreciation_board_id.asset_id",
    )
    asset_remaining_value = fields.Monetary(
        string="Depreciable Value",
        compute="_compute_depreciation_cumulative_value",
    )
    asset_depreciated_value = fields.Monetary(
        string="Cumulative Depreciation",
        compute="_compute_depreciation_cumulative_value",
    )
    asset_value_change = fields.Boolean()
    asset_number_days = fields.Integer(
        string="Number of days",
        copy=False,
    )
    asset_depreciation_beginning_date = fields.Date(
        string="Date of the beginning of the depreciation",
        copy=False,
    )
    depreciation_value = fields.Monetary(
        string="Depreciation",
        compute="_compute_depreciation_value",
        inverse="_inverse_depreciation_value",
        store=True,
    )

    capitalised_board_ids = fields.One2many(
        comodel_name="account.depreciation.board",
        string="Assets",
        compute="_compute_capitalised_board_ids",
        compute_sudo=True,
    )
    capitalised_asset_ids = fields.Many2many(
        comodel_name="resource.asset",
        string="Capitalised Assets",
        compute="_compute_capitalised_board_ids",
        compute_sudo=True,
    )
    count_capitalised_asset = fields.Count(
        count_of="capitalised_board_ids",
        compute_sudo=True,
    )
    draft_asset_exists = fields.Boolean(
        compute="_compute_capitalised_board_ids",
        compute_sudo=True,
    )
    asset_move_type = fields.Selection(
        selection=[
            ("depreciation", "Depreciation"),
            ("sale", "Sale"),
            ("purchase", "Purchase"),
            ("disposal", "Disposal"),
            ("negative_revaluation", "Negative revaluation"),
            ("positive_revaluation", "Positive revaluation"),
        ],
        compute="_compute_asset_move_type",
        store=True,
        copy=False,
    )

    @api.depends(
        "depreciation_board_id",
        "depreciation_value",
        "depreciation_board_id.value_depreciable",
        "depreciation_board_id.value_depreciated_import",
        "state",
    )
    @_debug.perf.timed
    def _compute_depreciation_cumulative_value(self):
        self.asset_depreciated_value = 0
        self.asset_remaining_value = 0

        fields = [
            self._fields["asset_remaining_value"],
            self._fields["asset_depreciated_value"],
        ]
        with self.env.protecting(
            fields, self.depreciation_board_id.depreciation_move_ids
        ):
            for asset in self.depreciation_board_id:
                depreciated = asset.value_depreciated_import
                remaining = asset.value_depreciable - asset.value_depreciated_import
                for move in asset.depreciation_move_ids._sorted_by_date():
                    if move.state != "cancel":
                        remaining -= move.depreciation_value
                        depreciated += move.depreciation_value
                    move.asset_remaining_value = remaining
                    move.asset_depreciated_value = depreciated

    @api.depends("line_ids.balance")
    @_debug.perf.timed
    def _compute_depreciation_value(self):
        for move in self:
            asset = (
                move.depreciation_board_id
                or move.reversed_entry_id.depreciation_board_id
            )
            if asset:
                depreciation_lines = move._get_asset_depreciation_line()
                asset_depreciation = sum(depreciation_lines.mapped("balance"))
                initial_lines = move.line_ids.filtered(
                    lambda line: (
                        line.account_id == asset.account_asset_id  # noqa: B023  the lambda runs inside this iteration
                        and float_compare(
                            -line.balance,
                            asset.value_original,  # noqa: B023  the lambda runs inside this iteration
                            precision_rounding=asset.currency_id.rounding,  # noqa: B023  the lambda runs inside this iteration
                        )
                        == 0
                    )
                )
                if initial_lines and len(move.line_ids) > 2:
                    accumulated = (move.line_ids - initial_lines).filtered(
                        lambda line: line.account_id == asset.account_depreciation_id  # noqa: B023  the lambda runs inside this iteration
                    )[:1]
                    asset_depreciation = (
                        asset.value_original
                        - asset.value_salvage
                        - abs(accumulated.balance)
                        * (-1 if asset.value_original < 0 else 1)
                    )
            else:
                asset_depreciation = 0
            move.depreciation_value = asset_depreciation

    @api.depends("depreciation_board_id", "capitalised_board_ids")
    def _compute_asset_move_type(self):
        for move in self:
            if move.capitalised_board_ids:
                move.asset_move_type = (
                    "positive_revaluation"
                    if move.capitalised_board_ids.increased_board_id
                    else "purchase"
                )
            elif not (move.asset_move_type and move.depreciation_board_id):
                move.asset_move_type = False

    def _inverse_depreciation_value(self):
        for move in self:
            depreciation_line = move._get_asset_depreciation_line()
            counterpart_line = move.line_ids - depreciation_line
            if len(depreciation_line) != 1 or len(counterpart_line) != 1:
                _debug.logic(
                    "depreciation_value.refused", reason="not_two_lines", move=move
                )
                raise UserError(
                    _(
                        "The depreciation of %s cannot be set from the board: the entry "
                        "is not a plain two-line depreciation.",
                        move.display_name,
                    )
                )
            move.write(
                {
                    "line_ids": [
                        Command.update(
                            depreciation_line.id, {"balance": move.depreciation_value}
                        ),
                        Command.update(
                            counterpart_line.id, {"balance": -move.depreciation_value}
                        ),
                    ]
                }
            )

    @api.constrains("state", "depreciation_board_id")
    def _constrains_check_asset_state(self):
        for move in self.filtered(lambda mv: mv.depreciation_board_id):
            asset_id = move.depreciation_board_id
            if asset_id.depreciation_state == "draft" and move.state == "posted":
                _debug.logic(
                    "post.refused", reason="draft_board", move=move, board=asset_id
                )
                raise ValidationError(
                    _(
                        "You can't post an entry related to a draft asset. Please post the asset before."
                    )
                )

    def _post_entries(self):
        posted = super()._post_entries()

        posted._log_depreciation_asset()

        posted.sudo()._auto_create_asset()

        return posted

    def _reverse_moves(self, default_values_list=None, cancel=False):
        default_values_list = [
            dict(values) for values in default_values_list or [{} for _i in self]
        ]
        for move, default_values in zip(self, default_values_list, strict=True):
            if move.depreciation_board_id:
                first_draft = min(
                    move.depreciation_board_id.depreciation_move_ids.filtered(
                        lambda m: m.state == "draft"
                    ),
                    key=lambda m: m.date,
                    default=None,
                )
                if first_draft:
                    first_draft.depreciation_value += move.depreciation_value
                elif move.depreciation_board_id.depreciation_state != "close":
                    last_date = max(
                        move.depreciation_board_id.depreciation_move_ids.mapped("date")
                    )
                    depreciation_period = move.depreciation_board_id.depreciation_period

                    self.create(
                        self._prepare_move_for_asset_depreciation(
                            {
                                "asset_id": move.depreciation_board_id,
                                "amount": move.depreciation_value,
                                "depreciation_beginning_date": last_date
                                + (
                                    relativedelta(months=1)
                                    if depreciation_period == "1"
                                    else relativedelta(years=1)
                                ),
                                "date": last_date
                                + (
                                    relativedelta(months=1)
                                    if depreciation_period == "1"
                                    else relativedelta(years=1)
                                ),
                                "asset_number_days": 0,
                            }
                        )
                    )

                msg = _(
                    "Depreciation entry %(name)s reversed (%(value)s)",
                    name=move.name,
                    value=formatLang(
                        self.env,
                        move.depreciation_value,
                        currency_obj=move.company_id.currency_id,
                    ),
                )
                move.depreciation_board_id.message_post(body=msg)
                _debug.lifecycle(
                    "depreciation_entry_reversed",
                    move=move,
                    board=move.depreciation_board_id,
                    to_first_draft=bool(first_draft),
                )
                default_values["depreciation_board_id"] = move.depreciation_board_id.id
                default_values["asset_number_days"] = -move.asset_number_days
                default_values["asset_depreciation_beginning_date"] = (
                    default_values.get("date", move.date)
                )

        return super()._reverse_moves(default_values_list, cancel)

    def action_draft(self):
        for move in self:
            if any(
                board.depreciation_state != "draft"
                for board in move.capitalised_board_ids
            ):
                _debug.logic("draft.refused", reason="posted_board", move=move)
                raise UserError(
                    _("You cannot reset to draft an entry related to a posted asset")
                )
            drafts = move.capitalised_board_ids.filtered(
                lambda x: x.depreciation_state == "draft"
            )
            created = drafts.filtered("created_asset").asset_id
            drafts.unlink()
            created.unlink()
        return super().action_draft()

    def _log_depreciation_asset(self):
        for move in self.filtered(lambda m: m.depreciation_board_id):
            asset = move.depreciation_board_id
            msg = _(
                "Depreciation entry %(name)s posted (%(value)s)",
                name=move.name,
                value=formatLang(
                    self.env,
                    move.depreciation_value,
                    currency_obj=move.company_id.currency_id,
                ),
            )
            asset.message_post(body=msg)

    def _auto_create_asset(self):
        plans = []
        for move in self:
            if not move.is_invoice():
                continue
            for move_line in move.line_ids:
                if not move_line._creates_an_asset():
                    continue
                plans.extend(move_line._plan_assets())
        _debug.pipeline("assets_planned", moves=self, plans=len(plans))
        return self.env["account.depreciation.board"]._create_from_plans(plans)

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        missing_fields = {
            "asset_id",
            "amount",
            "depreciation_beginning_date",
            "date",
            "asset_number_days",
        } - set(vals)
        if missing_fields:
            _debug.logic(
                "depreciation_move.refused",
                reason="missing_fields",
                missing=sorted(missing_fields),
            )
            raise UserError(_("Some fields are missing %s", ", ".join(missing_fields)))
        asset = vals["asset_id"]
        analytic_distribution = asset.analytic_distribution
        depreciation_date = vals.get("date", fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount_currency = vals["amount"]
        amount = current_currency._convert(
            amount_currency, company_currency, asset.company_id, depreciation_date
        )
        partner = asset.original_move_line_ids.mapped("partner_id")
        partner = partner[:1] if len(partner) <= 1 else self.env["res.partner"]
        name = _("%s: Depreciation", asset.name)
        ref = vals.get("move_ref") or name
        depreciates = float_compare(amount, 0.0, precision_digits=prec) > 0
        booked = amount if depreciates else -amount

        def depreciation_line(account, on_debit):
            line = {
                "name": name,
                "partner_id": partner.id,
                "account_id": account.id,
                "debit": booked if on_debit == depreciates else 0.0,
                "credit": 0.0 if on_debit == depreciates else booked,
                "currency_id": current_currency.id,
                "amount_currency": amount_currency if on_debit else -amount_currency,
            }
            if analytic_distribution:
                line["analytic_distribution"] = analytic_distribution
            return line

        return {
            "partner_id": partner.id,
            "date": depreciation_date,
            "journal_id": asset.depreciation_journal_id.id,
            "line_ids": [
                (0, 0, depreciation_line(asset.account_depreciation_id, False)),
                (
                    0,
                    0,
                    depreciation_line(asset.account_depreciation_expense_id, True),
                ),
            ],
            "depreciation_board_id": asset.id,
            "ref": ref,
            "asset_depreciation_beginning_date": vals["depreciation_beginning_date"],
            "asset_number_days": vals["asset_number_days"],
            "asset_value_change": vals.get("asset_value_change", False),
            "move_type": "entry",
            "currency_id": current_currency.id,
            "asset_move_type": vals.get("asset_move_type", "depreciation"),
            "company_id": asset.company_id.id,
        }

    def _sorted_by_date(self):
        return self.sorted(lambda move: (move.date, move._origin.id))

    def _is_effective_depreciation(self):
        self.check_singleton()
        return (
            self.state == "posted"
            and not self.reversal_move_ids
            and not self.reversed_entry_id
        )

    def _get_asset_depreciation_line(self):
        asset = self.depreciation_board_id
        expense_lines = self.line_ids.filtered(
            lambda line: line.account_id == asset.account_depreciation_expense_id
        )
        if expense_lines:
            return expense_lines
        excluded = (
            asset.account_asset_id
            + asset.account_depreciation_id
            + asset.company_id.gain_account_id
            + asset.company_id.loss_account_id
        )
        return self.line_ids.filtered(
            lambda line: (
                line.account_id.internal_group == "expense"
                and line.account_id not in excluded
            )
        )

    @api.depends("line_ids.capitalised_board_ids")
    def _compute_capitalised_board_ids(self):
        for record in self:
            record.capitalised_board_ids = record.line_ids.capitalised_board_ids
            record.capitalised_asset_ids = record.capitalised_board_ids.asset_id
            record.draft_asset_exists = bool(
                record.capitalised_board_ids.filtered(
                    lambda x: x.depreciation_state == "draft"
                )
            )

    def open_asset_view(self):
        return self.depreciation_board_id.open_board(["form"])

    def action_view_capitalised_asset_ids(self):
        return self.capitalised_board_ids.open_board(["list", "form"])


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    capitalised_board_ids = fields.Many2many(
        comodel_name="account.depreciation.board",
        relation="depreciation_board_move_line_rel",
        column1="line_id",
        column2="board_id",
        string="Related Assets",
        copy=False,
        context={"active_test": False},
    )
    capitalised_asset_ids = fields.Many2many(
        comodel_name="resource.asset",
        string="Capitalised Assets",
        compute="_compute_capitalised_asset_ids",
    )

    @api.depends("capitalised_board_ids.asset_id")
    def _compute_capitalised_asset_ids(self):
        for line in self:
            line.capitalised_asset_ids = line.capitalised_board_ids.asset_id

    non_deductible_tax_value = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_non_deductible_tax_value",
    )

    def _creates_an_asset(self):
        self.check_singleton()
        account = self.account_id
        move = self.move_id
        return bool(
            account
            and account.can_create_asset
            and account.create_asset != "no"
            and not (self.currency_id or move.currency_id).is_zero(self.price_total)
            and not self.capitalised_board_ids
            and not self.tax_line_id
            and self.price_total > 0
            and not (
                move.move_type in ("out_invoice", "out_refund")
                and account.internal_group == "asset"
            )
        )

    def _plan_assets(self):
        # Several profiles on one account describe one purchase from several angles
        # (a depreciable half and a non-depreciable one), so the first board lands
        # on the asset and each further one on a component of it. A line naming an
        # asset never creates an unrelated root: its board joins that asset, or
        # becomes its component when it already depreciates.
        self.check_singleton()
        account = self.account_id
        units = max(1, int(self.quantity)) if account.multiple_assets_per_line else 1
        named = (
            self.asset_id if "asset_id" in self._fields else self.env["resource.asset"]
        )
        base_vals = self._get_asset_vals()
        profiles = account.depreciation_profile_ids.filtered(
            lambda profile: profile.company_id in self.company_id.parent_ids
        )
        plans = []
        for unit in range(1, units + 1):
            for position, profile in enumerate(
                list(profiles) or [self.env["account.depreciation.profile"]]
            ):
                vals = dict(base_vals)
                if profile:
                    vals["depreciation_profile_id"] = profile.id
                    defaults = profile._get_asset_defaults()
                    defaults.pop("account_asset_id", None)
                    vals.update(defaults)
                if units > 1:
                    vals["name"] = _(
                        "%(move_line)s (%(current)s of %(total)s)",
                        move_line=self.name,
                        current=unit,
                        total=units,
                    )
                plans.append(
                    {
                        "vals": vals,
                        "move": self.move_id,
                        "validate": account.create_asset == "validate",
                        "named_asset": named,
                        "profile": profile,
                        "unit": (self.id, unit),
                        "component_of_unit": position > 0,
                    }
                )
        _debug.pipeline(
            "line_planned",
            line=self,
            units=units,
            profiles=len(profiles),
            plans=len(plans),
        )
        return plans

    def _get_asset_vals(self):
        self.check_singleton()
        move = self.move_id
        if not self.name:
            if not self.product_id:
                _debug.logic("asset_vals.refused", reason="no_label", line=self)
                raise UserError(
                    _(
                        "Journal Items of %(account)s should have a label in order to generate an asset",
                        account=self.account_id.display_name,
                    )
                )
            self.name = self.product_id.display_name
        return {
            "name": self.name,
            "company_id": self.company_id.id,
            "analytic_distribution": self.analytic_distribution,
            "original_move_line_ids": [Command.set(self.ids)],
            "depreciation_state": "draft",
            "date_acquisition": move.invoice_date
            if not move.reversed_entry_id
            else move.reversed_entry_id.invoice_date,
        }

    def _get_computed_taxes(self):
        if self.move_id.depreciation_board_id:
            return self.tax_ids
        return super()._get_computed_taxes()

    def turn_as_asset(self):
        if len(self.company_id) != 1:
            _debug.logic(
                "turn_as_asset.refused", reason="several_companies", lines=self
            )
            raise UserError(_("All the lines should be from the same company"))
        if any(line.move_id.state == "draft" for line in self):
            _debug.logic("turn_as_asset.refused", reason="draft_moves", lines=self)
            raise UserError(_("All the lines should be posted"))
        if any(account != self[0].account_id for account in self.mapped("account_id")):
            _debug.logic("turn_as_asset.refused", reason="several_accounts", lines=self)
            raise UserError(_("All the lines should be from the same account"))
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_original_move_line_ids": [Command.set(self.ids)],
                "default_company_id": self.company_id.id,
            }
        )
        return {
            "name": _("Turn as an asset"),
            "type": "ir.actions.act_window",
            "res_model": "account.depreciation.board",
            "views": [[False, "form"]],
            "target": "current",
            "context": ctx,
        }

    @api.depends(
        "tax_ids.invoice_repartition_line_ids",
        "balance",
        "quantity",
        "move_id.line_ids.balance",
    )
    @_debug.perf.timed
    def _compute_non_deductible_tax_value(self):
        non_deductible_tax_ids = self.tax_ids.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax" and not line.use_in_tax_closing
        ).tax_id

        res = {}
        if non_deductible_tax_ids and self.ids:
            domain = [("move_id", "in", self.move_id.ids)]
            tax_details_query = self._get_query_tax_details_from_domain(domain)

            self.flush_model()
            self.env.cr.execute(
                SQL(
                    """
                SELECT
                    tdq.base_line_id,
                    SUM(tdq.tax_amount_currency)
                FROM (%(tax_details_query)s) AS tdq
                JOIN account_move_line aml ON aml.id = tdq.tax_line_id
                JOIN account_tax_repartition_line trl ON trl.id = tdq.tax_repartition_line_id
                WHERE tdq.base_line_id IN %(base_line_ids)s
                AND trl.use_in_tax_closing IS FALSE
                GROUP BY tdq.base_line_id
                """,
                    tax_details_query=tax_details_query,
                    base_line_ids=tuple(self.ids),
                )
            )

            res = {
                row["base_line_id"]: row["sum"] for row in self.env.cr.dictfetchall()
            }
            _debug.perf.count("non_deductible_tax_read", lines=self, rows=len(res))

        for record in self:
            record.non_deductible_tax_value = res.get(record._origin.id, 0.0)
