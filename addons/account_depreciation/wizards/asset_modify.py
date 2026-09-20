from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_is_zero
from odoo.tools.misc import format_date

_debug = DebugLog(__name__)


class AssetModify(models.TransientModel):
    """Pauses, resumes, disposes of, sells or reduces an asset, generating the corresponding depreciation adjustment."""

    _name = "asset.modify"
    _description = "Modify Asset"
    _check_company_auto = True

    name = fields.Text(string="Note")
    asset_id = fields.Many2one(
        comodel_name="account.depreciation.board",
        required=True,
        ondelete="cascade",
        help="The depreciation board this wizard modifies",
    )
    depreciation_duration = fields.Integer(
        string="Duration",
        required=True,
    )
    depreciation_period = fields.Selection(
        selection=[("1", "Months"), ("12", "Years")],
        string="Number of Months in a Period",
        help="The amount of time between two depreciations",
    )
    value_depreciable_residual = fields.Monetary(
        string="Depreciable Amount",
        compute="_compute_value_depreciable_residual",
        store=True,
        readonly=False,
        help="New residual amount for the asset",
    )
    value_salvage = fields.Monetary(
        string="Not Depreciable Amount",
        help="New salvage amount for the asset",
    )
    currency_id = fields.Many2one(related="asset_id.currency_id")
    date = fields.Date(default=lambda self: fields.Date.today())
    select_invoice_line_id = fields.Boolean(compute="_compute_select_invoice_line_id")
    gain_value = fields.Boolean(compute="_compute_gain_value")

    account_asset_id = fields.Many2one(
        comodel_name="account.account",
        string="Gross Increase Account",
        check_company=True,
    )
    account_asset_counterpart_id = fields.Many2one(
        comodel_name="account.account",
        string="Asset Counterpart Account",
        check_company=True,
    )
    account_depreciation_id = fields.Many2one(
        comodel_name="account.account",
        string="Depreciation Account",
        check_company=True,
    )
    account_depreciation_expense_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        check_company=True,
    )
    modify_action = fields.Selection(
        selection="_selection_modify_action",
        string="Action",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="asset_id.company_id",
    )

    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Customer Invoice",
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]",
        check_company=True,
        help="The disposal invoice is needed in order to generate the closing journal entry.",
    )
    invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        domain="[('move_id', 'in', invoice_ids), ('display_type', '=', 'product')]",
        check_company=True,
        help="There are multiple lines that could be the related to this asset",
    )
    gain_account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_accounts",
        inverse="_inverse_gain_account",
        compute_sudo=True,
        readonly=False,
        check_company=True,
        help="Account used to write the journal item in case of gain",
    )
    loss_account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_accounts",
        inverse="_inverse_loss_account",
        compute_sudo=True,
        readonly=False,
        check_company=True,
        help="Account used to write the journal item in case of loss",
    )

    informational_text = fields.Html(compute="_compute_informational_text")

    gain_or_loss = fields.Selection(
        selection=[("gain", "Gain"), ("loss", "Loss"), ("no", "No")],
        compute="_compute_gain_or_loss",
    )

    def _selection_modify_action(self):
        if self.env.context.get("resume_after_pause"):
            return [("resume", _("Resume"))]
        return [
            ("dispose", _("Dispose")),
            ("sell", _("Sell")),
            ("modify", _("Re-evaluate")),
            ("pause", _("Pause")),
        ]

    @api.depends("company_id")
    def _compute_accounts(self):
        for record in self:
            record.gain_account_id = record.company_id.gain_account_id
            record.loss_account_id = record.company_id.loss_account_id

    @api.depends("date", "asset_id")
    def _compute_value_depreciable_residual(self):
        for record in self:
            record.value_depreciable_residual = (
                record.asset_id._get_residual_value_at_date(record.date)
            )

    def _inverse_gain_account(self):
        for record in self:
            record.company_id.sudo().gain_account_id = record.gain_account_id

    def _inverse_loss_account(self):
        for record in self:
            record.company_id.sudo().loss_account_id = record.loss_account_id

    @api.onchange("modify_action")
    def _onchange_action(self):
        if self.modify_action == "sell" and self.asset_id.increase_ids.filtered(
            lambda a: (
                a.depreciation_state in ("draft", "open")
                or a.value_depreciable_residual > 0
            )
        ):
            _debug.logic("sell.refused", reason="running_increase", board=self.asset_id)
            raise UserError(
                _(
                    "You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."
                )
            )
        if self.modify_action not in ("modify", "resume"):
            self.write(
                {
                    "value_depreciable_residual": self.asset_id._get_residual_value_at_date(
                        self.date
                    ),
                    "value_salvage": self.asset_id.value_salvage,
                }
            )

    @api.onchange("invoice_ids")
    def _onchange_invoice_ids(self):
        self.invoice_line_ids = self.invoice_ids.invoice_line_ids.filtered(
            lambda line: line._origin.id in self.invoice_line_ids.ids
        )
        for invoice in self.invoice_ids.filtered(
            lambda inv: len(inv.invoice_line_ids) == 1
        ):
            self.invoice_line_ids += invoice.invoice_line_ids

    @api.depends("asset_id", "invoice_ids", "invoice_line_ids", "modify_action", "date")
    def _compute_gain_or_loss(self):
        for record in self:
            balances = abs(sum(line.balance for line in record.invoice_line_ids))
            comparison = record.company_id.currency_id.compare_amounts(
                record.asset_id._get_own_book_value(record.date), balances
            )
            if record.modify_action in ("sell", "dispose") and comparison < 0:
                record.gain_or_loss = "gain"
            elif record.modify_action in ("sell", "dispose") and comparison > 0:
                record.gain_or_loss = "loss"
            else:
                record.gain_or_loss = "no"

    @api.depends("asset_id", "value_depreciable_residual", "value_salvage")
    def _compute_gain_value(self):
        for record in self:
            record.gain_value = (
                record.currency_id.compare_amounts(
                    record._get_requested_book_value(),
                    record.asset_id._get_own_book_value(record.date),
                )
                > 0
            )

    def _get_outcome_account_name(self):
        self.check_singleton()
        outcome_account = {
            "gain": self.gain_account_id,
            "loss": self.loss_account_id,
        }.get(self.gain_or_loss, self.env["account.account"])
        return outcome_account.display_name or ""

    def _get_value_increase_text(self):
        self.check_singleton()
        if not self.gain_value:
            return ""
        return _("An asset will be created for the value increase of the asset. <br/>")

    @api.depends(
        "loss_account_id",
        "gain_account_id",
        "gain_or_loss",
        "modify_action",
        "date",
        "value_depreciable_residual",
        "value_salvage",
    )
    def _compute_informational_text(self):
        for wizard in self:
            account = wizard._get_outcome_account_name()
            if wizard.modify_action == "dispose":
                gain_or_loss = {"gain": _("gain"), "loss": _("loss")}.get(
                    wizard.gain_or_loss, _("gain/loss")
                )
                wizard.informational_text = _(
                    "A depreciation entry will be posted on and including the date %(date)s."
                    "<br/> A disposal entry will be posted on the %(account_type)s account <b>%(account)s</b>.",
                    date=format_date(self.env, wizard.date),
                    account_type=gain_or_loss,
                    account=account,
                )
            elif wizard.modify_action == "sell":
                wizard.informational_text = _(
                    "A depreciation entry will be posted on and including the date %(date)s."
                    "<br/> A second entry will neutralize the original income and post the  "
                    "outcome of this sale on account <b>%(account)s</b>.",
                    date=format_date(self.env, wizard.date),
                    account=account,
                )
            elif wizard.modify_action == "pause":
                wizard.informational_text = _(
                    "A depreciation entry will be posted on and including the date %s.",
                    format_date(self.env, wizard.date),
                )
            elif wizard.modify_action == "modify":
                wizard.informational_text = _(
                    "A depreciation entry will be posted on and including the date %(date)s. <br/> %(extra_text)s "
                    "Future entries will be recomputed to depreciate the asset following the changes.",
                    date=format_date(self.env, wizard.date),
                    extra_text=wizard._get_value_increase_text(),
                )

            else:
                wizard.informational_text = _(
                    "%s Future entries will be recomputed to depreciate the asset following the changes.",
                    wizard._get_value_increase_text(),
                )

    @api.depends("invoice_ids", "modify_action")
    def _compute_select_invoice_line_id(self):
        for record in self:
            record.select_invoice_line_id = (
                record.modify_action == "sell"
                and len(record.invoice_ids.invoice_line_ids) > 1
            )

    INHERITED_FROM_ASSET = (
        "depreciation_duration",
        "depreciation_period",
        "value_salvage",
        "account_asset_id",
        "account_depreciation_id",
        "account_depreciation_expense_id",
    )

    @api.model_create_multi
    def create(self, vals_list):
        Board = self.env["account.depreciation.board"]
        for vals in vals_list:
            if "asset_id" not in vals:
                continue
            asset = Board.browse(vals["asset_id"])
            if asset.depreciation_move_ids.filtered(
                lambda m: (
                    m.state == "posted"
                    and not m.reversal_move_ids
                    and m.date > fields.Date.today()
                )
            ):
                _debug.logic(
                    "create.refused", reason="future_posted_entries", board=asset
                )
                raise UserError(
                    _(
                        "Reverse the depreciation entries posted in the future in order to modify the depreciation"
                    )
                )
            for fname in self.INHERITED_FROM_ASSET:
                if fname not in vals:
                    value = asset[fname]
                    vals[fname] = value.id if Board._fields[fname].relational else value
        return super().create(vals_list)

    def _check_can_modify(self):
        self.check_singleton()
        if self.date <= self.asset_id.company_id._get_user_fiscal_lock_date(
            self.asset_id.depreciation_journal_id
        ):
            _debug.logic(
                "modify.refused", reason="before_lock_date", wizard=self, date=self.date
            )
            raise UserError(_("You can't re-evaluate the asset before the lock date."))
        if self.env.context.get("resume_after_pause"):
            return
        if self.env["account.move"].search_count(
            [
                ("depreciation_board_id", "=", self.asset_id.id),
                ("state", "=", "draft"),
                ("date", "<=", self.date),
            ],
            limit=1,
        ):
            _debug.logic(
                "modify.refused",
                reason="unposted_before_date",
                wizard=self,
                date=self.date,
            )
            raise UserError(
                _(
                    "There are unposted depreciations prior to the selected operation date, please deal with them first."
                )
            )

    def _get_resume_after_pause_vals(self):
        self.check_singleton()
        date_before_pause = (
            max(self.asset_id.depreciation_move_ids, key=lambda x: x.date).date
            if self.asset_id.depreciation_move_ids
            else self.asset_id.date_acquisition
        )
        number_days = self.asset_id._get_delta_days(date_before_pause, self.date) - 1
        if number_days < 0:
            _debug.logic(
                "resume.refused",
                reason="date_before_pause",
                wizard=self,
                days=number_days,
            )
            raise UserError(
                _("You cannot resume at a date equal to or before the pause date")
            )
        return {
            "depreciation_paused_days": self.asset_id.depreciation_paused_days
            + number_days,
            "depreciation_state": "open",
        }

    def _create_gross_increase(self, residual_increase, salvage_increase):
        self.check_singleton()
        increase_total = residual_increase + salvage_increase
        label = _("Value increase for: %(asset)s", asset=self.asset_id.name)
        move = self.env["account.move"].create(
            {
                "journal_id": self.asset_id.depreciation_journal_id.id,
                "date": self.date + relativedelta(days=1),
                "move_type": "entry",
                "asset_move_type": "positive_revaluation",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_asset_id.id,
                            "debit": increase_total,
                            "credit": 0,
                            "name": label,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.account_asset_counterpart_id.id,
                            "debit": 0,
                            "credit": increase_total,
                            "name": label,
                        }
                    ),
                ],
            }
        )
        move._post()
        asset_increase = self.env["account.depreciation.board"].create(
            {
                "created_asset": True,
                "name": f"{self.asset_id.name}: {self.name}"
                if self.name
                else self.asset_id.name,
                "company_id": self.asset_id.company_id.id,
                "depreciation_method": self.asset_id.depreciation_method,
                "depreciation_duration": self.depreciation_duration,
                "depreciation_period": self.depreciation_period,
                "depreciation_factor": self.asset_id.depreciation_factor,
                "date_acquisition": self.date + relativedelta(days=1),
                "value_salvage": salvage_increase,
                "date_prorata": self.date + relativedelta(days=1),
                "depreciation_prorata": "daily_computation"
                if self.asset_id.depreciation_prorata == "daily_computation"
                else "constant_periods",
                "value_original": self._get_increase_original_value(
                    residual_increase, salvage_increase
                ),
                "account_asset_id": self.account_asset_id.id,
                "account_depreciation_id": self.account_depreciation_id.id,
                "account_depreciation_expense_id": self.account_depreciation_expense_id.id,
                "depreciation_journal_id": self.asset_id.depreciation_journal_id.id,
                "parent_id": self.asset_id.asset_id.id,
                "increased_board_id": self.asset_id.id,
                "kind_id": self.asset_id.kind_id.id,
                "original_move_line_ids": [
                    Command.set(
                        move.line_ids.filtered(
                            lambda line: line.account_id == self.account_asset_id
                        ).ids
                    )
                ],
            }
        )
        asset_increase.action_confirm()
        _debug.lifecycle(
            "gross_increase_created",
            board=self.asset_id,
            increase=asset_increase,
            amount=increase_total,
        )
        self.asset_id.message_post(
            body=_(
                "A gross increase has been created: %(link)s",
                link=asset_increase._get_html_link(),
            )
        )
        return asset_increase

    def _create_value_decrease(self, decrease):
        self.check_singleton()
        move = self.env["account.move"].create(
            self.env["account.move"]._prepare_move_for_asset_depreciation(
                {
                    "amount": decrease,
                    "asset_id": self.asset_id,
                    "move_ref": _(
                        "Value decrease for: %(asset)s", asset=self.asset_id.name
                    ),
                    "depreciation_beginning_date": self.date,
                    "date": self.date,
                    "asset_number_days": 0,
                    "asset_value_change": True,
                    "asset_move_type": "negative_revaluation",
                }
            )
        )
        move._post()
        _debug.lifecycle("value_decrease_posted", board=self.asset_id, move=move)
        return move

    @staticmethod
    def _rebuild_board(asset, restart_date):
        if asset.depreciation_move_ids:
            asset._create_depreciation_entries(restart_date)
        else:
            asset._create_depreciation_entries()

    def _propagate_to_children(self, asset_vals, restart_date):
        self.check_singleton()
        children = self.asset_id.increase_ids
        if not children:
            return
        _debug.pipeline("propagate_to_children", board=self.asset_id, children=children)
        children.write(
            {
                "depreciation_duration": asset_vals["depreciation_duration"],
                "depreciation_period": asset_vals["depreciation_period"],
                "depreciation_paused_days": self.asset_id.depreciation_paused_days,
            }
        )
        for child in children:
            if not self.env.context.get("resume_after_pause"):
                child._create_move_before_date(self.date)
            self._rebuild_board(child, restart_date)
            child._check_depreciations()
            child.depreciation_move_ids.filtered(
                lambda move: move.state != "posted"
            )._post()

    def _log_board_modification(self, old_values):
        self.check_singleton()
        tracked_fields = self.asset_id.fields_get(old_values.keys())
        changes, tracking_value_ids = self.asset_id._mail_track(
            tracked_fields, old_values
        )
        if changes:
            self.asset_id.message_post(
                body=_("Depreciation board modified %s", self.name),
                tracking_value_ids=tracking_value_ids,
            )

    def action_modify(self):
        self.check_singleton()
        self._check_can_modify()
        resuming = bool(self.env.context.get("resume_after_pause"))

        old_values = {
            "depreciation_duration": self.asset_id.depreciation_duration,
            "depreciation_period": self.asset_id.depreciation_period,
            "value_depreciable_residual": self.asset_id.value_depreciable_residual,
            "value_salvage": self.asset_id.value_salvage,
        }
        asset_vals = {
            "depreciation_duration": self.depreciation_duration,
            "depreciation_period": self.depreciation_period,
            "account_asset_id": self.account_asset_id,
            "account_depreciation_id": self.account_depreciation_id,
            "account_depreciation_expense_id": self.account_depreciation_expense_id,
        }
        if resuming:
            asset_vals.update(self._get_resume_after_pause_vals())
            self.asset_id.message_post(body=_("Asset unpaused. %s", self.name))

        current_asset_book = self.asset_id._get_own_book_value(self.date)
        increase = self._get_requested_book_value() - current_asset_book
        new_residual, new_salvage = self._get_new_asset_values(current_asset_book)
        residual_increase = max(0, self.value_depreciable_residual - new_residual)
        salvage_increase = max(0, self.value_salvage - new_salvage)

        if not resuming:
            self.asset_id._create_move_before_date(self.date)

        asset_vals["value_salvage"] = new_salvage
        computation_children_changed = (
            asset_vals["depreciation_duration"] != self.asset_id.depreciation_duration
            or asset_vals["depreciation_period"] != self.asset_id.depreciation_period
            or (
                asset_vals.get("depreciation_paused_days")
                and not float_is_zero(
                    asset_vals["depreciation_paused_days"]
                    - self.asset_id.depreciation_paused_days,
                    8,
                )
            )
        )
        self.asset_id.write(asset_vals)

        if (
            self.currency_id.compare_amounts(residual_increase + salvage_increase, 0)
            > 0
        ):
            self._create_gross_increase(residual_increase, salvage_increase)
        if self.currency_id.compare_amounts(increase, 0) < 0:
            self._create_value_decrease(-increase)

        restart_date = self.date if resuming else self.date + relativedelta(days=1)
        _debug.pipeline(
            "modify",
            wizard=self,
            board=self.asset_id,
            resuming=resuming,
            residual_increase=residual_increase,
            salvage_increase=salvage_increase,
            decrease=-increase if increase < 0 else 0.0,
            children_changed=computation_children_changed,
            restart=restart_date,
        )
        self._rebuild_board(self.asset_id, restart_date)
        if computation_children_changed:
            self._propagate_to_children(asset_vals, restart_date)

        self._log_board_modification(old_values)
        self.asset_id._check_depreciations()
        self.asset_id.depreciation_move_ids.filtered(
            lambda move: move.state != "posted"
        )._post()
        return {"type": "ir.actions.act_window_close"}

    def action_pause(self):
        for record in self:
            record.asset_id._pause(date=record.date, message=record.name)

    def action_sell_dispose(self):
        self.check_singleton()
        if self.asset_id.account_depreciation_id in (
            self.gain_account_id,
            self.loss_account_id,
        ):
            _debug.logic(
                "sell_dispose.refused",
                reason="outcome_is_depreciation_account",
                wizard=self,
            )
            raise UserError(
                _("You cannot select the same account as the Depreciation Account")
            )
        invoice_lines = (
            self.env["account.move.line"]
            if self.modify_action == "dispose"
            else self.invoice_line_ids
        )
        return self.asset_id._close(
            invoice_line_ids=invoice_lines, date=self.date, message=self.name
        )

    def _get_requested_book_value(self):
        return self.value_depreciable_residual + self.value_salvage

    def _get_increase_original_value(self, residual_increase, salvage_increase):
        return residual_increase + salvage_increase

    def _get_new_asset_values(self, current_asset_book):
        self.check_singleton()
        new_residual = min(
            current_asset_book - min(self.value_salvage, self.asset_id.value_salvage),
            self.value_depreciable_residual,
        )
        new_salvage = min(current_asset_book - new_residual, self.value_salvage)
        return new_residual, new_salvage
