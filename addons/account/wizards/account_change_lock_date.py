from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils

from odoo.addons.account.models.account_config import (
    LOCK_DATE_FIELDS,
    SOFT_LOCK_DATE_FIELDS,
)

_debug = DebugLog(__name__)


class AccountChangeLockDate(models.TransientModel):
    _name = "account.change.lock.date"
    _description = "Change Lock Date"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )

    fiscalyear_lock_date = fields.Date(
        string="Lock Everything",
        compute="_compute_lock_dates",
        precompute=True,
        store=True,
        readonly=False,
        help="Any entry up to and including that date will be postponed to a later time, in accordance with its journal's sequence.",
    )
    fiscalyear_lock_date_for_me = fields.Date(
        string="Lock Everything For Me",
        compute="_compute_lock_date_exceptions",
    )
    fiscalyear_lock_date_for_everyone = fields.Date(
        string="Lock Everything For Everyone",
        compute="_compute_lock_date_exceptions",
    )
    min_fiscalyear_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )
    min_fiscalyear_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )

    tax_lock_date = fields.Date(
        string="Lock Tax Return",
        compute="_compute_lock_dates",
        precompute=True,
        store=True,
        readonly=False,
        help="Any entry with taxes up to and including that date will be postponed to a later time, in accordance with its journal's sequence. "
        "The tax lock date is automatically set when the tax closing entry is posted.",
    )
    tax_lock_date_for_me = fields.Date(
        string="Lock Tax Return For Me",
        compute="_compute_lock_date_exceptions",
    )
    tax_lock_date_for_everyone = fields.Date(
        string="Lock Tax Return For Everyone",
        compute="_compute_lock_date_exceptions",
    )
    min_tax_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )
    min_tax_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )

    sale_lock_date = fields.Date(
        string="Lock Sales",
        compute="_compute_lock_dates",
        precompute=True,
        store=True,
        readonly=False,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    sale_lock_date_for_me = fields.Date(
        string="Lock Sales For Me",
        compute="_compute_lock_date_exceptions",
    )
    sale_lock_date_for_everyone = fields.Date(
        string="Lock Sales For Everyone",
        compute="_compute_lock_date_exceptions",
    )
    min_sale_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )
    min_sale_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )

    purchase_lock_date = fields.Date(
        string="Lock Purchases",
        compute="_compute_lock_dates",
        precompute=True,
        store=True,
        readonly=False,
        help="Any purchase entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    purchase_lock_date_for_me = fields.Date(
        string="Lock Purchases For Me",
        compute="_compute_lock_date_exceptions",
    )
    purchase_lock_date_for_everyone = fields.Date(
        string="Lock Purchases For Everyone",
        compute="_compute_lock_date_exceptions",
    )
    min_purchase_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )
    min_purchase_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name="account.lock_exception",
        compute="_compute_lock_date_exceptions",
    )

    hard_lock_date = fields.Date(
        string="Hard Lock",
        compute="_compute_lock_dates",
        precompute=True,
        store=True,
        readonly=False,
        help="Any entry up to and including that date will be postponed to a later time, in accordance with its journal sequence. "
        "This lock date is irreversible and does not allow any exception.",
    )
    current_hard_lock_date = fields.Date(
        related="company_id.account_config_id.hard_lock_date",
        string="Current Hard Lock",
        readonly=True,
    )

    exception_needed_fields = fields.Char(compute="_compute_exception_needed_fields")
    exception_applies_to = fields.Selection(
        selection=[
            ("me", "for me"),
            ("everyone", "for everyone"),
        ],
        string="Exception applies",
        default="me",
        required=True,
    )
    exception_duration = fields.Selection(
        selection=[
            ("5min", "for 5 minutes"),
            ("15min", "for 15 minutes"),
            ("1h", "for 1 hour"),
            ("24h", "for 24 hours"),
            ("forever", "forever"),
        ],
        default="5min",
        required=True,
    )
    exception_reason = fields.Char()

    show_draft_entries_warning = fields.Boolean(
        compute="_compute_show_draft_entries_warning"
    )

    show_posted_tax_closing_warning = fields.Boolean(
        compute="_compute_show_posted_tax_closing_warning"
    )

    @api.depends("company_id")
    def _compute_lock_dates(self):
        for wizard in self:
            for field in LOCK_DATE_FIELDS:
                wizard[field] = wizard.company_id.account_config_id[field]

    @api.depends("company_id")
    @api.depends_context("uid", "company")
    @_debug.perf.timed
    def _compute_lock_date_exceptions(self):
        for wizard in self:
            exceptions = self.env["account.lock_exception"].search(  # noqa: E8507 - a transient wizard opened on one company
                self.env["account.lock_exception"]._get_domain_active_exceptions(
                    wizard.company_id, SOFT_LOCK_DATE_FIELDS
                )
            )
            for field in SOFT_LOCK_DATE_FIELDS:
                field_exceptions = exceptions.filtered(
                    lambda e, field=field: e.lock_date_field == field
                )
                field_exceptions_for_me = field_exceptions.filtered(
                    lambda e: e.user_id.id == self.env.user.id
                )
                field_exceptions_for_everyone = field_exceptions.filtered(
                    lambda e: not e.user_id.id
                )
                min_exception_for_me = (
                    min(field_exceptions_for_me, key=lambda e: e[field] or date.min)
                    if field_exceptions_for_me
                    else False
                )
                min_exception_for_everyone = (
                    min(
                        field_exceptions_for_everyone,
                        key=lambda e: e[field] or date.min,
                    )
                    if field_exceptions_for_everyone
                    else False
                )
                wizard[f"min_{field}_exception_for_me_id"] = min_exception_for_me
                wizard[f"min_{field}_exception_for_everyone_id"] = (
                    min_exception_for_everyone
                )
                wizard[f"{field}_for_me"] = (
                    min_exception_for_me.lock_date if min_exception_for_me else False
                )
                wizard[f"{field}_for_everyone"] = (
                    min_exception_for_everyone.lock_date
                    if min_exception_for_everyone
                    else False
                )
            _debug.pipeline(
                "active_lock_exceptions_found",
                company=wizard.company_id,
                exceptions=exceptions,
            )

    def _get_domain_draft_moves_in_locked_period(self):
        self.check_singleton()
        lock_date_domains = []
        if self.hard_lock_date:
            lock_date_domains.append([("date", "<=", self.hard_lock_date)])
        if self.fiscalyear_lock_date:
            lock_date_domains.append([("date", "<=", self.fiscalyear_lock_date)])
        if self.sale_lock_date:
            lock_date_domains.append(
                [("date", "<=", self.sale_lock_date), ("journal_id.type", "=", "sale")]
            )
        if self.purchase_lock_date:
            lock_date_domains.append(
                [
                    ("date", "<=", self.purchase_lock_date),
                    ("journal_id.type", "=", "purchase"),
                ]
            )
        if self.tax_lock_date:
            lock_date_domains.append(
                [
                    ("date", "<=", self.tax_lock_date),
                    ("line_ids.tax_ids", "!=", False),
                ]
            )
        _debug.logic(
            "draft_moves_lock_domain_built",
            wizard=self,
            lock_dates=len(lock_date_domains),
            no_lock_dates=not lock_date_domains,
        )
        return (
            Domain("company_id", "child_of", self.company_id.id)
            & Domain("state", "=", "draft")
            & Domain.OR(lock_date_domains)
        )

    @api.depends(
        "fiscalyear_lock_date",
        "tax_lock_date",
        "sale_lock_date",
        "purchase_lock_date",
        "hard_lock_date",
    )
    def _compute_show_draft_entries_warning(self):
        for wizard in self:
            draft_entries = self.env["account.move"].search(  # noqa: E8507 - a transient wizard opened on one company
                wizard._get_domain_draft_moves_in_locked_period(), limit=1
            )
            wizard.show_draft_entries_warning = bool(draft_entries)

    def _get_domain_posted_tax_closings_in_locked_period(self):
        self.check_singleton()
        return [
            ("company_id", "child_of", self.company_id.id),
            ("date", ">", self.tax_lock_date),
            (
                "closing_return_id.type_id.report_id.root_report_id",
                "=",
                self.env.ref("account.generic_tax_report").id,
            ),
            ("state", "=", "posted"),
        ]

    @api.depends("tax_lock_date")
    def _compute_show_posted_tax_closing_warning(self):
        for wizard in self:
            wizard.show_posted_tax_closing_warning = bool(
                wizard.tax_lock_date
                and self.env["account.move"].search(  # noqa: E8507 - a transient wizard opened on one company
                    wizard._get_domain_posted_tax_closings_in_locked_period(), limit=1
                )
            )

    def _get_changes_needing_exception(self):
        self.check_singleton()
        return {
            field: self[field]
            for field in SOFT_LOCK_DATE_FIELDS
            if self.company_id.account_config_id[field]
            and (
                not self[field]
                or self[field] < self.company_id.account_config_id[field]
            )
        }

    @api.depends(*SOFT_LOCK_DATE_FIELDS)
    def _compute_exception_needed_fields(self):
        for wizard in self:
            changes_needing_exception = wizard._get_changes_needing_exception()
            wizard.exception_needed_fields = ",".join(changes_needing_exception)

    @_debug.perf.timed
    def _prepare_lock_date_values(self, exception_vals_list=None):
        self.check_singleton()
        if self.company_id.account_config_id.hard_lock_date and (
            not self.hard_lock_date
            or self.hard_lock_date < self.company_id.account_config_id.hard_lock_date
        ):
            _debug.logic(
                "lock_date_change_rejected", wizard=self, reason="hard_lock_decreased"
            )
            raise UserError(
                _("It is not possible to decrease or remove the Hard Lock Date.")
            )

        lock_date_values = {
            field: self[field]
            for field in LOCK_DATE_FIELDS
            if self[field] != self.company_id.account_config_id[field]
        }

        for lock_date in lock_date_values.values():
            if lock_date and lock_date > fields.Date.context_today(self):
                _debug.logic(
                    "lock_date_change_rejected",
                    wizard=self,
                    reason="future_date",
                    lock_date=lock_date,
                )
                raise UserError(_("You cannot set a Lock Date in the future."))

        if exception_vals_list:
            for exception_vals in exception_vals_list:
                for field in LOCK_DATE_FIELDS:
                    if field in exception_vals:
                        lock_date_values.pop(field, None)

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "lock_date_values_prepared",
                wizard=self,
                fields=sorted(lock_date_values),
                exceptions=len(exception_vals_list or ()),
            )
        return lock_date_values

    @_debug.perf.timed
    def _prepare_exception_values(self):
        self.check_singleton()
        changes_needing_exception = self._get_changes_needing_exception()

        if _debug.logic.enabled:
            _debug.logic(
                "lock_changes_needing_exception",
                company=self.company_id,
                fields=sorted(changes_needing_exception or ()),
            )
        if not changes_needing_exception:
            return False

        _debug.logic(
            "exception_scope_chosen",
            applies_to=self.exception_applies_to,
            duration=self.exception_duration,
            skipped=self.exception_applies_to == "everyone"
            and self.exception_duration == "forever",
        )

        if (
            self.exception_applies_to == "everyone"
            and self.exception_duration == "forever"
        ):
            return False

        exception_errors = []
        if not self.exception_applies_to:
            exception_errors.append(
                _("You need to select who the exception applies to.")
            )
        if not self.exception_duration:
            exception_errors.append(
                _("You need to select a duration for the exception.")
            )
        if exception_errors:
            raise UserError("\n".join(exception_errors))

        exception_base_values = {
            "company_id": self.company_id.id,
        }

        exception_base_values["user_id"] = {
            "me": self.env.user.id,
            "everyone": False,
        }[self.exception_applies_to]

        exception_timedelta = {
            "5min": timedelta(minutes=5),
            "15min": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "forever": False,
        }[self.exception_duration]
        if exception_timedelta:
            exception_base_values["end_datetime"] = (
                self.env.cr.now() + exception_timedelta
            )

        if self.exception_reason:
            exception_base_values["reason"] = self.exception_reason

        _debug.pipeline(
            "exception_values_prepared",
            company=self.company_id,
            count=len(changes_needing_exception),
            expires=bool(exception_timedelta),
            user_id=exception_base_values.get("user_id"),
        )
        return [
            {
                **exception_base_values,
                field: value,
            }
            for field, value in changes_needing_exception.items()
        ]

    def _get_current_period_dates(self, lock_date_field):
        self.check_singleton()
        company_lock_date = self.company_id.account_config_id[lock_date_field]
        if company_lock_date:
            date_from = company_lock_date + timedelta(days=1)
        else:
            date_from = date_utils.get_fiscal_year(self[lock_date_field])[0]
        return date_from, self[lock_date_field]

    def _create_default_report_external_values(self, lock_date_field):
        pass

    def _change_lock_date(self, lock_date_values=None):
        self.check_singleton()
        if lock_date_values is None:
            lock_date_values = self._prepare_lock_date_values()

        tax_lock_date = lock_date_values.get("tax_lock_date", None)
        if (
            tax_lock_date
            and tax_lock_date != self.company_id.account_config_id["tax_lock_date"]
        ):
            self._create_default_report_external_values("tax_lock_date")

        fiscalyear_lock_date = lock_date_values.get("fiscalyear_lock_date", None)
        hard_lock_date = lock_date_values.get("hard_lock_date", None)
        if fiscalyear_lock_date or hard_lock_date:
            fiscal_lock_date, field = max(
                [
                    (fiscalyear_lock_date, "fiscalyear_lock_date"),
                    (hard_lock_date, "hard_lock_date"),
                ],
                key=lambda t: t[0] or date.min,
            )
            company_fiscal_lock_date = max(
                self.company_id.account_config_id.fiscalyear_lock_date or date.min,
                self.company_id.account_config_id.hard_lock_date or date.min,
            )
            if fiscal_lock_date != company_fiscal_lock_date:
                self._create_default_report_external_values(field)

        _debug.pipeline(
            "company",
            lockdate=self,
            company_id=self.company_id,
            lock_date_values=lock_date_values,
        )
        self.company_id.sudo().write(lock_date_values)

    def change_lock_date(self):
        self.check_singleton()
        if self.env.user.has_group("account.group_account_manager"):
            exception_vals_list = self._prepare_exception_values()
            changed_lock_date_values = self._prepare_lock_date_values(
                exception_vals_list=exception_vals_list
            )

            if exception_vals_list:
                _debug.logic(
                    "creating_exception",
                    lockdate=self,
                    exception_vals_list_count=len(exception_vals_list),
                )
                self.env["account.lock_exception"].create(exception_vals_list)

            self._change_lock_date(changed_lock_date_values)
        else:
            raise UserError(
                _("Only Billing Administrators are allowed to change lock dates!")
            )
        return {"type": "ir.actions.act_window_close"}

    @_debug.perf.timed
    def action_show_draft_moves_in_locked_period(self):
        _debug.lifecycle("action_show_draft_moves_in_locked_period", records=self)
        self.check_singleton()
        return {
            "view_mode": "list",
            "name": _("Draft Entries"),
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "domain": self._get_domain_draft_moves_in_locked_period(),
            "search_view_id": [
                self.env.ref("account.view_account_move_filter").id,
                "search",
            ],
            "views": [
                [self.env.ref("account.view_move_tree_multi_edit").id, "list"],
                [self.env.ref("account.view_move_form").id, "form"],
            ],
        }

    @_debug.perf.timed
    def action_show_posted_tax_closing_in_locked_period(self):
        _debug.lifecycle(
            "action_show_posted_tax_closing_in_locked_period", records=self
        )
        self.check_singleton()
        posted_closings = self.env["account.move"].search(
            self._get_domain_posted_tax_closings_in_locked_period()
        )
        return self.env["account.return"].action_view_tax_return_view(
            additional_return_domain=[
                ("id", "in", posted_closings.closing_return_id.ids)
            ]
        )

    @_debug.perf.timed
    def action_reopen_wizard(self):
        _debug.lifecycle("action_reopen_wizard", records=self)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @_debug.perf.timed
    def action_revoke_min_exception(self):
        _debug.lifecycle("action_revoke_min_exception", records=self)
        self.check_singleton()
        lock_date_field = self.env.context.get("lock_date_field")
        scope = self.env.context.get("exception_scope")
        if lock_date_field not in SOFT_LOCK_DATE_FIELDS or scope not in (
            "me",
            "everyone",
        ):
            _debug.logic(
                "min_exception_revoke_rejected",
                wizard=self,
                lock_date_field=lock_date_field,
                scope=scope,
            )
            raise UserError(
                _(
                    "Unknown lock date exception to revoke: %(field)s / %(scope)s.",
                    field=lock_date_field,
                    scope=scope,
                )
            )

        exception = self[f"min_{lock_date_field}_exception_for_{scope}_id"]
        _debug.logic(
            "min_exception_revoke",
            wizard=self,
            lock_date_field=lock_date_field,
            scope=scope,
            exceptions=exception,
        )
        if exception:
            exception.action_revoke()
            self._compute_lock_date_exceptions()
        return self.action_reopen_wizard()
