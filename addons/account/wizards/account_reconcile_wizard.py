from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountReconcileWizard(models.TransientModel):
    _name = "account.reconcile.wizard"
    _description = "Account reconciliation wizard"
    _check_company_auto = True

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields)
        if "move_line_ids" not in fields:
            return res
        if self.env.context.get(
            "active_model"
        ) != "account.move.line" or not self.env.context.get("active_ids"):
            raise UserError(_("This can only be used on journal items"))
        move_line_ids = self.env["account.move.line"].browse(
            self.env.context["active_ids"]
        )
        accounts = move_line_ids.account_id
        if len(accounts) > 2:
            raise UserError(
                _(
                    "You can only reconcile entries with up to two different accounts: %s",
                    ", ".join(accounts.mapped("display_name")),
                )
            )
        shadowed_aml_values = None
        if len(accounts) == 2:
            shadowed_aml_values = {
                aml: {"account_id": move_line_ids[0].account_id}
                for aml in move_line_ids.filtered(
                    lambda line: line.account_id != move_line_ids[0].account_id
                )
            }
        _debug.logic(
            "reconcile_accounts_checked",
            lines=move_line_ids,
            accounts=len(accounts),
            shadowed=bool(shadowed_aml_values),
        )
        move_line_ids._check_amls_exigibility_for_reconciliation(
            shadowed_aml_values=shadowed_aml_values
        )
        res["move_line_ids"] = [Command.set(move_line_ids.ids)]
        return res

    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        readonly=True,
        required=True,
    )
    move_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Move lines to reconcile",
        required=True,
    )
    reco_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Reconcile Account",
        compute="_compute_reco_wizard_data",
    )
    amount = fields.Monetary(
        string="Amount in company currency",
        currency_field="company_currency_id",
        compute="_compute_reco_wizard_data",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company currency",
    )
    amount_currency = fields.Monetary(
        string="Amount",
        currency_field="reco_currency_id",
        compute="_compute_reco_wizard_data",
    )
    reco_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency to use for reconciliation",
        compute="_compute_reco_wizard_data",
    )
    edit_mode_amount = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_edit_mode_amount",
    )
    edit_mode_amount_currency = fields.Monetary(
        string="Edit mode amount",
        currency_field="edit_mode_reco_currency_id",
        compute="_compute_edit_mode_amount_currency",
        store=True,
        readonly=False,
    )
    edit_mode_reco_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_edit_mode_reco_currency_id",
    )
    edit_mode = fields.Boolean(compute="_compute_edit_mode")
    single_currency_mode = fields.Boolean(compute="_compute_single_currency_mode")
    allow_partials = fields.Boolean(
        string="Allow partials",
        compute="_compute_allow_partials",
        store=True,
        readonly=False,
    )
    force_partials = fields.Boolean(compute="_compute_reco_wizard_data")
    display_allow_partials = fields.Boolean(compute="_compute_display_allow_partials")
    date = fields.Date(
        compute="_compute_date",
        store=True,
        readonly=False,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('type', '=', 'general')]",
        check_company=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('account_type', '!=', 'off_balance')]",
        check_company=True,
    )
    is_rec_pay_account = fields.Boolean(compute="_compute_is_rec_pay_account")
    to_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        compute="_compute_to_partner_id",
        store=True,
        readonly=False,
        check_company=True,
    )
    label = fields.Char(default="Write-Off")
    tax_id = fields.Many2one(
        comodel_name="account.tax",
        default=False,
        check_company=True,
    )
    to_check = fields.Boolean(
        default=False,
        help="Check if you are not certain of all the information of the counterpart.",
    )
    is_write_off_required = fields.Boolean(
        string="Is a write-off move required to reconcile",
        compute="_compute_is_write_off_required",
    )
    is_transfer_required = fields.Boolean(
        string="Is an account transfer required",
        compute="_compute_reco_wizard_data",
    )
    transfer_warning_message = fields.Char(
        string="Is an account transfer required to reconcile",
        compute="_compute_reco_wizard_data",
    )
    transfer_from_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account Transfer From",
        compute="_compute_reco_wizard_data",
    )
    lock_date_violated_warning_message = fields.Char(
        string="Is the date violating the lock date of moves",
        compute="_compute_lock_date_violated_warning_message",
    )
    reco_model_id = fields.Many2one(
        comodel_name="account.reconcile.model",
        string="Reconciliation model",
        store=False,
        check_company=True,
    )
    reco_model_autocomplete_ids = fields.Many2many(
        comodel_name="account.reconcile.model",
        string="All reconciliation models",
        compute="_compute_reco_model_autocomplete_ids",
    )

    @api.depends("move_line_ids.company_id")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.move_line_ids[0].company_id

    @api.depends("move_line_ids")
    def _compute_single_currency_mode(self):
        for wizard in self:
            wizard.single_currency_mode = (
                len(wizard.move_line_ids.currency_id - wizard.company_currency_id) <= 1
            )

    @api.depends("force_partials")
    def _compute_allow_partials(self):
        for wizard in self:
            wizard.allow_partials = (
                wizard.display_allow_partials and wizard.force_partials
            )

    @api.depends("move_line_ids")
    def _compute_display_allow_partials(self):
        for wizard in self:
            wizard.display_allow_partials = has_debit_line = has_credit_line = False
            for aml in wizard.move_line_ids:
                if aml.balance > 0.0 or aml.amount_currency > 0.0:
                    has_debit_line = True
                elif aml.balance < 0.0 or aml.amount_currency < 0.0:
                    has_credit_line = True
                if has_debit_line and has_credit_line:
                    wizard.display_allow_partials = True
                    break

    @api.depends("move_line_ids", "journal_id", "tax_id")
    def _compute_date(self):
        for wizard in self:
            highest_date = max(aml.date for aml in wizard.move_line_ids)
            temp_move = self.env["account.move"].new(
                {"journal_id": wizard.journal_id.id}
            )
            wizard.date = temp_move._get_accounting_date(
                highest_date, bool(wizard.tax_id)
            )

    @api.depends("company_id")
    def _compute_journal_id(self):
        for wizard in self:
            wizard.journal_id = self.env["account.journal"].search(  # noqa: E8507 - a transient wizard opened on one company
                [
                    *self.env["account.journal"]._check_company_domain(
                        wizard.company_id
                    ),
                    ("type", "=", "general"),
                ],
                limit=1,
            )

    @api.depends("account_id")
    def _compute_is_rec_pay_account(self):
        for wizard in self:
            wizard.is_rec_pay_account = wizard.account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            )

    @api.depends("is_rec_pay_account")
    def _compute_to_partner_id(self):
        for wizard in self:
            if wizard.is_rec_pay_account:
                partners = wizard.move_line_ids.partner_id
                wizard.to_partner_id = partners if len(partners) == 1 else None
            else:
                wizard.to_partner_id = None

    @api.depends("amount", "amount_currency")
    def _compute_is_write_off_required(self):
        for wizard in self:
            wizard.is_write_off_required = not wizard.company_currency_id.is_zero(
                wizard.amount
            ) or (
                wizard.reco_currency_id
                and not wizard.reco_currency_id.is_zero(wizard.amount_currency)
            )

    @api.constrains("edit_mode_amount_currency")
    @_debug.perf.timed
    def _check_min_max_edit_mode_amount_currency(self):
        for wizard in self:
            if wizard.edit_mode:
                if wizard.edit_mode_reco_currency_id.is_zero(
                    wizard.edit_mode_amount_currency
                ):
                    _debug.logic(
                        "edit_mode_amount_rejected", recwizard=wizard, reason="zero"
                    )
                    raise UserError(
                        _("The amount of the write-off of a single line cannot be 0.")
                    )
                is_debit_line = (
                    wizard.move_line_ids.balance > 0.0
                    or wizard.move_line_ids.amount_currency > 0.0
                )
                if is_debit_line and wizard.edit_mode_amount_currency < 0.0:
                    _debug.logic(
                        "edit_mode_amount_rejected",
                        recwizard=wizard,
                        reason="negative_on_debit_line",
                    )
                    raise UserError(
                        _(
                            "The amount of the write-off of a single debit line should be strictly positive."
                        )
                    )
                if not is_debit_line and wizard.edit_mode_amount_currency > 0.0:
                    _debug.logic(
                        "edit_mode_amount_rejected",
                        recwizard=wizard,
                        reason="positive_on_credit_line",
                    )
                    raise UserError(
                        _(
                            "The amount of the write-off of a single credit line should be strictly negative."
                        )
                    )

    @_debug.perf.timed
    def _action_view_wizard(self):
        _debug.lifecycle("_action_view_wizard", records=self)
        self.check_singleton()
        return {
            "name": _("Write-Off Entry"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.reconcile.wizard",
            "target": "new",
        }

    def _get_date_after_lock_date(self):
        self.check_singleton()
        lock_dates = self.company_id._get_violated_lock_dates(
            self.date, bool(self.tax_id), self.journal_id
        )
        if lock_dates:
            return lock_dates[-1][0] + timedelta(days=1)
        return None

    @_debug.perf.timed
    def reconcile(self):
        self.check_singleton()
        move_lines_to_reconcile = self.move_line_ids._origin
        do_transfer = self.is_transfer_required
        do_write_off = self.edit_mode or (
            self.is_write_off_required and not self.allow_partials
        )
        _debug.logic(
            "reconcile",
            recwizard=self,
            move_lines_to_reconcile=move_lines_to_reconcile,
            transfer=do_transfer,
            write_off=do_write_off,
            partials=self.allow_partials,
            edit=self.edit_mode,
        )
        if do_transfer:
            transfer_move = self.create_transfer()
            lines_to_transfer = move_lines_to_reconcile.filtered(
                lambda line: line.account_id == self.transfer_from_account_id
            )
            transfer_line_from = transfer_move.line_ids.filtered(
                lambda line: line.account_id == self.transfer_from_account_id
            )
            transfer_line_to = transfer_move.line_ids.filtered(
                lambda line: line.account_id == self.reco_account_id
            )
            (lines_to_transfer + transfer_line_from).reconcile()
            move_lines_to_reconcile = (
                move_lines_to_reconcile - lines_to_transfer + transfer_line_to
            )

        if do_write_off:
            write_off_move = self.create_write_off()
            write_off_line_to_reconcile = write_off_move.line_ids[0]
            move_lines_to_reconcile += write_off_line_to_reconcile
            amls_plan = [[move_lines_to_reconcile, write_off_line_to_reconcile]]
        else:
            amls_plan = [move_lines_to_reconcile]

        self.env["account.move.line"]._reconcile_plan(amls_plan)
        return (
            move_lines_to_reconcile
            if not do_transfer
            else (move_lines_to_reconcile + transfer_move.line_ids)
        )

    def reconcile_open(self):
        self.check_singleton()
        return self.reconcile().open_reconcile_view()
