import ast
import base64
import json
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, Command, _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.translate import LazyTranslate

_debug = DebugLog(__name__)

_lt = LazyTranslate(__name__)


LIMIT_CHECK_ENTRIES = 21


def check_company_domain_account_return(self, companies):
    company_ids = models.to_record_ids(companies)
    if not companies:
        return [("company_ids", "=", False)]

    return [("company_ids", "in", company_ids)]


class AccountReturn(models.Model):
    _name = "account.return"
    _inherit = ["mixin.mail.thread.main.attachment", "mixin.mail.activity"]
    _description = "Accounting Return"
    _order = "is_completed, date_deadline, name, id"
    _check_company_domain = check_company_domain_account_return

    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    type_id = fields.Many2one(
        comodel_name="account.return.type",
        string="Return Type",
        required=True,
    )

    # IMPORTANT: To change the state of a return you should always write on the 'state' field; its
    # inverse dispatches the value to the selection field named by type_id.states_workflow.
    state = fields.Char(
        compute="_compute_state",
        inverse="_inverse_state",
        store=True,
    )
    next_state = fields.Char(compute="_compute_next_state")
    generic_state_tax_report = fields.Selection(
        selection=[
            ("new", "New"),
            ("reviewed", "Review"),
            ("submitted", "Submit"),
            ("paid", "Pay"),
        ],
        string="Generic State",
        default="new",
        tracking=True,
        help="The state of the return for generic tax report flows",
    )
    generic_state_only_pay = fields.Selection(
        selection=[
            ("new", "New"),
            ("paid", "Pay"),
        ],
        default="new",
        tracking=True,
        help="The state of the return for report flows when only payment is needed",
    )
    generic_state_review_submit = fields.Selection(
        selection=[
            ("new", "New"),
            ("reviewed", "Review"),
            ("submitted", "Submit"),
        ],
        default="new",
        tracking=True,
        help="The state of the return for report flows when review and submission are needed",
    )
    generic_state_review = fields.Selection(
        selection=[
            ("new", "New"),
            ("reviewed", "Review"),
        ],
        default="new",
        tracking=True,
        help="The default state for audit and custom generated return types",
    )
    is_completed = fields.Boolean(
        default=False,
        tracking=True,
    )  # Set to true when all steps are done
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
    )
    tax_unit_id = fields.Many2one(comodel_name="account.tax.unit")
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        compute="_compute_company_ids",
        precompute=True,
        compute_sudo=True,
        store=True,
    )
    closing_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="closing_return_id",
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        bypass_search_access=True,
    )
    type_external_id = fields.Char(compute="_compute_type_external_id")
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        store=True,
    )
    date_lock = fields.Date(string="Lock Date")
    date_submission = fields.Date(string="Submission Date")
    check_ids = fields.One2many(
        comodel_name="account.return.check",
        inverse_name="return_id",
        string="Checks",
    )
    check_count = fields.Count(
        count_of="check_ids",
        string="Checks Count",
    )
    unresolved_check_count = fields.Integer(
        string="Issues",
        compute="_compute_unresolved_check_count",
    )
    resolved_check_count = fields.Integer(
        string="Passed",
        compute="_compute_resolved_check_count",
    )
    manually_created = fields.Boolean()

    # Tax return fields
    total_amount_to_pay = fields.Monetary(currency_field="amount_to_pay_currency_id")
    period_amount_to_pay = fields.Monetary(currency_field="amount_to_pay_currency_id")
    amount_to_pay_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_amount_to_pay_currency_id",
    )
    show_amount_to_pay = fields.Boolean(compute="_compute_show_amount_to_pay")

    # view helper fields
    days_to_deadline = fields.Integer(compute="_compute_days_to_deadline")
    is_report_set = fields.Boolean(compute="_compute_is_report_set")
    has_move_entries = fields.Boolean(compute="_compute_has_move_entries")
    report_opened_once = fields.Boolean(
        default=False,
        help="Has the report been opened once",
    )
    report_name = fields.Char(
        related="type_id.report_id.display_name",
        string="Report Name",
    )
    show_companies = fields.Boolean(compute="_compute_show_companies")
    show_companies_mismatch_warning = fields.Boolean(
        compute="_compute_show_companies_mismatch_warning"
    )
    is_main_company_active = fields.Boolean(compute="_compute_is_main_company_active")
    return_type_category = fields.Selection(related="type_id.category")
    visible_states = fields.Json(compute="_compute_visible_states")
    show_submit_button = fields.Boolean(compute="_compute_show_submit_button")
    is_tax_return = fields.Boolean(related="type_id.is_tax_return_type")
    is_ec_sales_list_return = fields.Boolean(
        related="type_id.is_ec_sales_list_return_type"
    )

    # Audit
    audit_status = fields.Selection(
        selection=[
            ("ongoing", "Ongoing"),
            ("done", "Done"),
            ("paused", "Paused"),
        ],
        default="ongoing",
        required=True,
        tracking=True,
    )

    audit_account_status_ids = fields.One2many(
        comodel_name="account.audit.account.status",
        inverse_name="audit_id",
        string="Account Status",
    )
    audit_balances_count = fields.Integer(
        string="Balances Count",
        compute="_compute_audit_balances_count",
    )
    audit_balances_completed_count = fields.Integer(
        string="Completed Balances Count",
        compute="_compute_audit_balances_completed_count",
    )
    skipped_check_cycles = fields.Char()

    def _update_translated_name(self):
        specified_lang = self.env.context.get("update_returns_translation_lang")

        for account_return in self:
            type_id = account_return.type_id
            if specified_lang:
                translated_name_dict = {
                    specified_lang: type_id.with_context(
                        lang=specified_lang
                    )._get_return_name(
                        account_return.company_id,
                        account_return.date_from,
                        account_return.date_to,
                        minimal=False,
                        all_lang=False,
                    )
                }

            else:
                translated_name_dict = type_id._get_return_name(
                    account_return.company_id,
                    account_return.date_from,
                    account_return.date_to,
                    minimal=False,
                    all_lang=True,
                )

            for lang_code, translated_name in translated_name_dict.items():
                account_return.with_context(lang=lang_code).name = translated_name

    @api.deprecated(
        "Since 19.0, There's no need to have embedded.actions anymore for AccountReturnCheckControlPanel"
    )
    @_debug.perf.timed
    def _create_embedded_actions_config(self, audit_action_id):
        """Create embedded action settings for this return if not already existing."""
        user_setting_id = self.env.user.res_users_settings_id.id
        if self.env["res.users.settings.embedded.action"].search(
            [("user_setting_id", "=", user_setting_id), ("res_id", "=", self.id)],
        ):
            return None

        embedded_actions = self.env["ir.embedded.actions"].search(
            [
                ("parent_res_model", "=", "account.return"),
                ("parent_action_id", "=", audit_action_id),
            ],
        )
        user_actions = self.env["res.users.settings.embedded.action"].create(
            {
                "user_setting_id": user_setting_id,
                "action_id": audit_action_id,
                "res_id": self.id,
                "embedded_visibility": True,
                "res_model": self._name,
                "embedded_actions_visibility": ",".join(
                    ["false"]
                    + [str(a.id) for a in embedded_actions if not a.is_deletable]
                ),
            }
        )
        return user_actions._format_embedded_action_settings()

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        records = super().create(vals_list)
        account_status_create_vals = []
        for record in records:
            if record.return_type_category == "audit":
                accounts = self.env["account.account"].search_fetch(  # noqa: E8507 - audit returns are created one or two at a time; every probe is keyed by the return's own companies and period
                    domain=self.env["account.account"]._check_company_domain(
                        record.company_ids
                    ),
                    field_names=["id"],
                )
                eve_of_date_from = record.date_from - relativedelta(days=1)
                # The boundaries come from a fiscal calendar, and the periodicity,
                # the fiscal year and the start-date elements are all read off the
                # company: it has to be the return's own, not whichever one the
                # creating user happens to have active.
                date_from, date_to = record.type_id._get_period_boundaries(
                    record.company_id, eve_of_date_from
                )
                previous_return = self.env["account.return"].search(  # noqa: E8507 - audit returns are created one or two at a time; every probe is keyed by the return's own companies and period
                    domain=[
                        *self.env["account.return"]._check_company_domain(
                            record.company_id
                        ),
                        ("tax_unit_id", "=", record.tax_unit_id.id),
                        ("date_from", "=", date_from),
                        ("date_to", "=", date_to),
                        ("type_id", "=", record.type_id.id),
                    ],
                    limit=1,
                )
                previous_accounts_with_status = self.env["account.account"]
                if previous_return:
                    previous_accounts_with_status = (
                        self.env["account.audit.account.status"]
                        .search(  # noqa: E8507 - audit returns are created one or two at a time; every probe is keyed by the return's own companies and period
                            domain=[
                                ("audit_id", "=", previous_return.id),
                                ("status", "!=", False),
                            ],
                        )
                        .account_id
                    )
                aml_count_by_accounts = dict(
                    self.env["account.move.line"]._read_group(  # noqa: E8507 - audit returns are created one or two at a time; every probe is keyed by the return's own companies and period
                        # Scoped to the audit's own companies, as the account search
                        # above is: without it the entries that decide which accounts
                        # are "to review" are whichever ones the creating user happens
                        # to be allowed to see.
                        domain=[
                            *self.env["account.move.line"]._check_company_domain(
                                record.company_ids
                            ),
                            ("date", ">=", record.date_from),
                            ("date", "<=", record.date_to),
                            ("parent_state", "=", "posted"),
                        ],
                        groupby=["account_id"],
                        aggregates=["id:count_distinct"],
                    )
                )
                _debug.logic(
                    "audit_account_statuses_seeded",
                    tax_return=record,
                    previous_return=previous_return,
                    accounts=len(accounts),
                    accounts_with_entries=len(aml_count_by_accounts),
                    previously_reviewed=previous_accounts_with_status,
                )

                account_status_create_vals += [
                    {
                        "audit_id": record.id,
                        "account_id": account["id"],
                        "status": "todo"
                        if (account in previous_accounts_with_status)
                        or (account in aml_count_by_accounts)
                        else False,
                    }
                    for account in accounts
                ]
        _debug.pipeline(
            "audit_account_status_vals_prepared",
            tax_return=records,
            status_vals=len(account_status_create_vals),
        )
        self.env["account.audit.account.status"].create(account_status_create_vals)
        return records

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        result = super().write(vals)
        for record in self:
            if record.type_id.states_workflow in vals:
                if record.date_from <= fields.Date.end_of(
                    fields.Date.context_today(record), "month"
                ):
                    record.refresh_checks()

            if "audit_status" in vals:
                if record.audit_status in ("ongoing", "paused"):
                    record.state = "new"
        return result

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_if_not_manually_created_new(self):
        _debug.lifecycle("_unlink_if_not_manually_created_new", records=self)
        if (
            not self.env.user.has_group("account.group_account_user")
            and not self.env.su
        ):
            _debug.logic("unlink_rejected", tax_return=self, reason="not_accountant")
            raise UserError(self.env._("Only an Accountant can delete a return."))
        if (
            any(
                not account_return.manually_created or account_return.state != "new"
                for account_return in self
            )
            and not self.env.su
        ):
            _debug.logic("unlink_rejected", tax_return=self, reason="not_manual_new")
            raise UserError(
                self.env._(
                    "Only manually created returns in 'new' state can be deleted."
                )
            )

    @api.model
    @_debug.perf.timed
    def action_refresh_all_returns(self):
        _debug.lifecycle("action_refresh_all_returns", records=self)
        root_companies = (
            self.env["res.company"]
            .sudo()
            .search(
                [
                    ("account_opening_date", "!=", False),
                    ("id", "parent_of", self.env.companies.ids),
                ]
            )
        )
        self.env["account.return.type"]._sync_all_returns(root_companies)

    @api.model
    @_debug.perf.timed
    def _evaluate_deadline(
        self, company, return_type, return_type_external_id, date_from, date_to
    ):
        return_type_delay = return_type.with_company(company).deadline_days_delay
        delay = return_type_delay or company.account_return_reminder_day
        return date_to + relativedelta(days=delay)

    @api.depends(
        "date_to",
        "company_id.account_return_reminder_day",
        "type_id.deadline_days_delay",
        "is_completed",
    )
    def _compute_date_deadline(self):
        for account_return in self:
            if account_return.is_completed:
                continue

            account_return.date_deadline = account_return._evaluate_deadline(
                account_return.company_id,
                account_return.type_id,
                account_return.type_external_id,
                account_return.date_from,
                account_return.date_to,
            )

    @api.model
    def _get_company_ids(self, main_company, tax_unit, report):
        companies = (
            tax_unit.company_ids
            if tax_unit
            else self.env["res.company"]
            .sudo()
            .search([("id", "child_of", main_company.id)])
        )

        if report:
            previous_options = {"tax_unit": tax_unit.id if tax_unit else "company_only"}
            options = (
                report.sudo()
                .with_context(allowed_company_ids=companies.ids)
                .with_company(main_company.id)
                .get_options(previous_options=previous_options)
            )
            return self.env["res.company"].browse(
                report.get_report_company_ids(options)
            )

        return self.env["res.company"].browse(
            companies.ids
        )  # Drop sudo and avoid leaking elevated permissions

    @api.depends("company_id", "tax_unit_id", "type_id")
    def _compute_company_ids(self):
        company_ids_map = defaultdict(lambda: self.env["account.return"])
        for record in self:
            company_ids_map[
                record.company_id, record.tax_unit_id, record.type_id.report_id
            ] |= record

        for (company, tax_unit, report), returns in company_ids_map.items():
            returns.company_ids = self._get_company_ids(company, tax_unit, report)

    @api.depends_context("allowed_company_ids")
    @api.depends("company_ids")
    def _compute_show_companies(self):
        for record in self:
            # Use _get_company_ids() instead of company_ids: ir.rule filters records out during
            # cache insertion, so cached values may differ from those in the database and users
            # with branch-only access would see company_ids without the parent company.
            record.show_companies = (
                len(self.env.companies) > 1
                or len(
                    record._get_company_ids(
                        record.company_id, record.tax_unit_id, record.type_id.report_id
                    )
                )
                > 1
            )

    @_debug.perf.timed
    def _check_all_branches_allowed(self):
        for account_return in self:
            report = account_return.type_id.report_id
            if (
                account_return._get_company_ids(
                    account_return.company_id, False, report
                )
                - self.env.user.company_ids
            ):
                report.show_error_branch_allowed()

    @api.depends_context("allowed_company_ids")
    @api.depends("company_ids")
    def _compute_show_companies_mismatch_warning(self):
        for record in self:
            record.show_companies_mismatch_warning = bool(
                record.company_ids - self.env.companies
            )

    @api.depends_context("allowed_company_ids")
    @api.depends("company_ids")
    def _compute_is_main_company_active(self):
        for account_return in self:
            account_return.is_main_company_active = (
                account_return.company_id in self.env.companies
            )

    @api.depends("is_tax_return", "closing_move_ids")
    def _compute_show_amount_to_pay(self):
        for record in self:
            record.show_amount_to_pay = record.is_tax_return and record.closing_move_ids

    @api.depends("type_id", "type_id.states_workflow")
    def _compute_state(self):
        for record in self:
            record.state = record[record.type_id.states_workflow]

    @api.depends("state", "type_id.states_workflow")
    def _compute_next_state(self):
        for record in self:
            state_keys = [
                s[0] for s in record._fields[record.type_id.states_workflow].selection
            ]
            next_state_index = state_keys.index(record.state) + 1
            if next_state_index < len(state_keys):
                record.next_state = state_keys[next_state_index]
            else:
                record.next_state = False

    def _inverse_state(self):
        for record in self:
            record[record.type_id.states_workflow] = record.state

    @api.depends("type_id", "state", "type_id.states_workflow")
    @api.depends_context("lang")
    @_debug.perf.timed
    def _compute_visible_states(self):
        for record in self:
            current_state = record.state
            visible_states = []
            active = True
            for state, label in self._fields[
                record.type_id.states_workflow
            ]._description_selection(record.env):
                if state == current_state:
                    active = False

                if state != "new":
                    visible_states.append(
                        {
                            "active": active
                            or state == current_state
                            or record.is_completed,
                            "name": state,
                            "label": label,
                        }
                    )
            record.visible_states = visible_states

    @api.depends("tax_unit_id", "company_id")
    def _compute_amount_to_pay_currency_id(self):
        for record in self:
            record.amount_to_pay_currency_id = (
                record.tax_unit_id.main_company_id.sudo().currency_id
                or record.company_id.sudo().currency_id
            )

    @api.depends("state", "check_ids.state", "check_ids.result")
    def _compute_unresolved_check_count(self):
        for record in self:
            failed_count = 0
            for check in record.check_ids:
                failed_count += 1 if check.result in ("todo", "anomaly") else 0

            record.unresolved_check_count = failed_count

    @api.depends("check_ids", "unresolved_check_count", "state")
    def _compute_resolved_check_count(self):
        for record in self:
            record.resolved_check_count = (
                len(record.check_ids) - record.unresolved_check_count
            )

    @api.depends("type_id")
    def _compute_type_external_id(self):
        external_id_per_type = self.type_id.get_external_id()
        for record in self:
            record.type_external_id = external_id_per_type.get(record.type_id.id, None)

    @api.depends("type_id")
    def _compute_is_report_set(self):
        for record in self:
            record.is_report_set = record.type_id.report_id

    @api.depends("closing_move_ids")
    def _compute_has_move_entries(self):
        for record in self:
            record.has_move_entries = record.closing_move_ids

    @api.depends("date_deadline")
    def _compute_days_to_deadline(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.days_to_deadline = (
                (record.date_deadline - today).days if record.date_deadline else 0
            )

    @api.depends("audit_account_status_ids")
    def _compute_audit_balances_count(self):
        for record in self:
            record.audit_balances_count = len(
                record.audit_account_status_ids.filtered("status")
            )

    @api.depends("audit_account_status_ids")
    def _compute_audit_balances_completed_count(self):
        for record in self:
            record.audit_balances_completed_count = len(
                record.audit_account_status_ids.filtered(
                    lambda r: r.status in ("reviewed", "supervised")
                )
            )

    @api.depends("next_state")
    def _compute_show_submit_button(self):
        for record in self:
            record.show_submit_button = record.next_state == "submitted"

    @api.model
    def _get_return_from_report_options(self, options):
        report = self.env["account.report"].browse(options["report_id"])
        sender_company = report._get_sender_company_for_export(options)
        return self.env["account.return"].search(
            [
                ("company_id", "=", sender_company.id),
                ("date_from", "=", options["date"]["date_from"]),
                ("date_to", "=", options["date"]["date_to"]),
                ("type_id.report_id", "=", report.id),
            ],
            limit=1,
        )

    @api.model
    @_debug.perf.timed
    def get_next_returns_ids(
        self, journal_id=False, additional_domain=None, allow_multiple_by_types=False
    ):
        """Return the ids of the uncompleted returns to post next, one per return type unless
        allow_multiple_by_types is set.

        :param journal_id: restrict the returns to the company of this journal
        :param additional_domain: extra domain leaves narrowing down the returns
        :param allow_multiple_by_types: return every matching return instead of the first of each type
        :rtype: list
        """

        domain = [
            ("is_completed", "=", False),
            *(additional_domain or []),
        ]

        if journal_id:
            journal = self.env["account.journal"].browse(journal_id)
            domain += self.env["account.return"]._check_company_domain(
                journal.company_id
            )

        future_returns_by_type = self.search_fetch(
            domain=domain,
            field_names=["name", "date_deadline", "type_id", "id"],
        ).grouped("type_id")

        next_returns_ids = []
        for recordset in future_returns_by_type.values():
            if not allow_multiple_by_types:
                next_returns_ids.append(recordset[0].id)
            else:
                next_returns_ids.extend(record.id for record in recordset)
        _debug.pipeline(
            "next_returns_selected",
            journal=journal_id,
            types=len(future_returns_by_type),
            returns=len(next_returns_ids),
            multiple_by_type=allow_multiple_by_types,
        )

        return next_returns_ids

    @api.model
    @_debug.perf.timed
    def get_next_return_for_dashboard(self, journal_id=False):
        additional_domain = [
            ("date_to", "<", fields.Date.context_today(self)),
            ("return_type_category", "=", "account_return"),
        ]
        return_ids = self.get_next_returns_ids(
            journal_id=journal_id,
            additional_domain=additional_domain,
            allow_multiple_by_types=True,
        )

        account_returns = self.browse(return_ids)
        dashboard_return_dicts = []
        grouped_by_type = defaultdict(list)

        for account_return in account_returns:
            return_type = account_return.type_id
            grouped_by_type[return_type] += account_return

        for return_type, returns in grouped_by_type.items():
            returns.sort(key=lambda x: x.date_deadline)
            dashboard_return_dicts.append(
                {
                    "id": returns[0].id,
                    "date_deadline": returns[0].date_deadline,
                    "name": return_type.name,
                    "type_id": return_type.id,
                    "matched_returns_count": len(returns),
                }
            )
        _debug.pipeline(
            "dashboard_returns_grouped",
            journal=journal_id,
            tax_return=account_returns,
            types=len(dashboard_return_dicts),
        )
        return dashboard_return_dicts

    @api.model
    @_debug.perf.timed
    def action_view_tax_return_view(
        self, additional_return_domain=None, additional_context=None
    ):
        _debug.lifecycle("action_view_tax_return_view", records=self)
        company = self.env.company

        if not additional_context:
            additional_context = {}

        company._check_tax_return_configuration()
        # Fiscal year is automatically setup with default values as it is a required field
        if not company.account_opening_date:
            _debug.logic("opening_date_missing", company=company)
            if not self.env.user.has_group("account.group_account_manager"):
                raise UserError(
                    _(
                        "You first need to define an opening date for your accounting. Please contact your administrator."
                    )
                )

            new_wizard = self.env["account.financial.year.op"].create(
                {"company_id": company.id}
            )
            return {
                "type": "ir.actions.act_window",
                "name": _("Accounting Periods"),
                "view_mode": "form",
                "res_model": "account.financial.year.op",
                "res_id": new_wizard.id,
                "target": "new",
                "views": [
                    [
                        self.env.ref("account.setup_financial_year_opening_form").id,
                        "form",
                    ]
                ],
                "context": {
                    "dialog_size": "medium",
                    "open_account_return_on_save": True,
                    "additional_return_domain": additional_return_domain,
                    "additional_return_context": additional_context,
                },
            }

        return_action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_view_account_return"
        )

        if additional_return_domain:
            return_action["domain"] = additional_return_domain
        if additional_context:
            context = self.env["ir.actions.actions"]._eval_action_context(
                return_action["context"]
            )
            context.update(additional_context)
            return_action["context"] = str(context)
        _debug.logic(
            "return_action_customized",
            company=company,
            has_domain=bool(additional_return_domain),
            has_context=bool(additional_context),
        )
        return return_action

    @_debug.perf.timed
    def action_view_audit_return(self):
        _debug.lifecycle("action_view_audit_return", records=self)
        self.check_singleton()
        audit_action = (
            self.with_context(active_id=self.id, active_model=self._name)
            .env["ir.actions.act_window"]
            ._get_action_dict_by_xml_id("account.action_view_account_audit_checks")
        )
        return {
            **audit_action,
            "domain": [("return_id", "=", self.id)],
            "context": {
                "account_return_view_id": self.env.ref(
                    "account.account_return_kanban_view"
                ).id,
                "search_default_groupby_cycle": 1,
                "active_model": "account.return",
                "active_id": self.id,
                "max_number_opened_groups": 100000,
            },
        }

    @_debug.perf.timed
    def action_view_audit_balances(self):
        # Opens the balances list view; action_view_audit_return opens the check kanban.
        _debug.lifecycle("action_view_audit_balances", records=self)
        self.check_singleton()
        return {
            **self.with_context(active_id=self.id, active_model=self._name)
            .env["ir.actions.act_window"]
            ._get_action_dict_by_xml_id("account.action_view_account_balances"),
            "context": {
                "account_return_view_id": self.env.ref(
                    "account.account_return_kanban_view"
                ).id,
                "search_default_groupby_cycle": 1,
                "active_model": "account.return",
                "active_id": self.id,
                "max_number_opened_groups": 100000,
                "working_file_id": self.id,
            },
        }

    def _get_pay_wizard(self):
        """Return the payment wizard action. Override in l10n modules opening a specific wizard."""
        wizard = self.env["account.return.payment.wizard"].create(
            {
                "return_id": self.id,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Payment"),
            "res_model": "account.return.payment.wizard",
            "res_id": wizard.id,
            "views": [(False, "form")],
            "target": "new",
        }

    ####################################################################################################
    ####  State Actions
    ####################################################################################################

    @_debug.perf.timed
    def action_validate(self, bypass_failing_tests=False):
        """Review the checks, then complete an audit return or lock any other return.

        :param bypass_failing_tests: mark the failing checks as reviewed instead of blocking
        """
        _debug.lifecycle("action_validate", records=self)
        self.check_singleton()

        self._review_checks(bypass_failing_tests)
        _debug.pipeline(
            "validate",
            tax_return=self,
            category=self.return_type_category,
            bypass=bypass_failing_tests,
            state=self.state,
        )

        if self.return_type_category == "audit":
            self.state = "reviewed"
            return self._mark_completed()

        return self._proceed_with_locking()

    def _review_checks(self, bypass_failing_tests):
        self.refresh_checks()

        if bypass_failing_tests:
            self.check_ids.filtered(
                lambda check: check.result == "anomaly"
            ).result = "reviewed"

        self._check_failing_checks_in_current_stage()

    @_debug.perf.timed
    def _proceed_with_locking(self, options_to_inject=None):
        """Lock the return: generate the carryover values and the attachments of
        `_generate_locking_attachments`, create the closing entries for a tax return, then set
        date_lock and move the state to 'reviewed'.

        :param options_to_inject: report options overriding the computed closing report options
        """
        self.check_singleton()

        domain = [
            ("company_id", "=", self.company_id.id),
            ("type_id", "=", self.type_id.id),
            ("date_deadline", "<", self.date_deadline),
            ("date_lock", "=", False),
            ("is_completed", "=", False),
            ("return_type_category", "!=", "audit"),
        ]
        count = self.env["account.return"].search_count(domain, limit=1)
        if count:
            raise UserError(
                _(
                    "You cannot lock this return as there are previous returns that are waiting to be posted."
                )
            )

        self._check_failing_checks_in_current_stage()

        if report := self.type_id.report_id:
            options = {
                **self._get_closing_report_options(),
                **(options_to_inject or {}),
                "export_mode": "file",
            }

            report.with_context(
                allowed_company_ids=self.company_ids.ids
            )._create_carryover_external_values(options)
            self._generate_locking_attachments(options)

            if self.is_tax_return:
                _debug.pipeline("locking_tax_closing_entries", tax_return=self)
                # Create the tax closing move
                self._create_tax_closing_entries(options)

                # Reset any tax lock date exceptions
                self.env["account.lock_exception"].search(
                    [
                        ("company_id", "in", self.company_ids.ids),
                        ("state", "=", "active"),
                        ("lock_date_field", "=", "tax_lock_date"),
                    ]
                ).sudo().action_revoke()

                # Create default expressions for next period if necessary
                main_company = self.tax_unit_id.main_company_id or self.company_id
                if (
                    report.country_id
                    and report.country_id == main_company.account_fiscal_country_id
                    and (
                        not main_company.tax_lock_date
                        or self.date_to > main_company.tax_lock_date
                    )
                ):
                    for company in self.company_ids:
                        self.env["account.report"].with_company(
                            company
                        )._create_default_external_values(
                            self.date_from, self.date_to, True, company=company
                        )
                        company.sudo().tax_lock_date = self.date_to

                # Generate the carryover values.
                payable_accounts, receivable_accounts = (
                    self._get_tax_closing_payable_and_receivable_accounts()
                )
                self.period_amount_to_pay = (
                    self._evaluate_period_amount_to_pay_from_tax_closing_accounts(
                        payable_accounts, receivable_accounts
                    )
                )
                self.total_amount_to_pay = (
                    self._evaluate_total_amount_to_pay_from_tax_closing_accounts(
                        payable_accounts, receivable_accounts
                    )
                )

        self.date_lock = fields.Date.context_today(self)
        _debug.lifecycle(
            "locked",
            tax_return=self,
            date_lock=self.date_lock,
            workflow=self.type_id.states_workflow,
        )

        self.state = "reviewed"
        if self.type_id.states_workflow == "generic_state_review":
            return self._mark_completed()

        if self.is_tax_return:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "title": self.env._("Checks Validated"),
                    "message": self.env._(
                        "Closing entry posted and lock date applied."
                    ),
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return None

    def _get_tax_closing_payable_and_receivable_accounts(self):
        country = (
            self.type_id.report_id.country_id
            or self.company_id.account_fiscal_country_id
        )
        tax_groups_sudo = (
            self.env["account.tax"]
            .sudo()
            ._read_group(
                domain=[
                    *self.env["account.tax"]._check_company_domain(self.company_ids),
                    ("country_id", "=", country.id),
                    *self._get_domain_amount_to_pay_additional_tax(),
                ],
                aggregates=["tax_group_id:recordset"],
            )[0][0]
        )
        return (
            tax_groups_sudo.tax_payable_account_id,
            tax_groups_sudo.tax_receivable_account_id,
        )

    @_debug.perf.timed
    def _evaluate_period_amount_to_pay_from_tax_closing_accounts(
        self, payable_accounts, receivable_accounts
    ):
        amount = -sum(
            aml.balance
            for aml in self.closing_move_ids.line_ids
            if aml.account_id in payable_accounts + receivable_accounts
        )

        return self.amount_to_pay_currency_id.round(amount)

    @_debug.perf.timed
    def _evaluate_total_amount_to_pay_from_tax_closing_accounts(
        self, payable_accounts, receivable_accounts
    ):
        recoverable_amount_to_pay = (
            self.env["account.move.line"]
            .sudo()
            ._read_group(
                [
                    ("date", "<=", self.date_to),
                    ("account_id", "in", receivable_accounts.ids),
                    ("company_id", "in", self.company_ids.ids),
                    ("move_id.state", "=", "posted"),
                    ("id", "not in", self.closing_move_ids.line_ids.ids),
                ],
                aggregates=["balance:sum"],
            )[0][0]
        )
        return self.amount_to_pay_currency_id.round(
            -recoverable_amount_to_pay + self.period_amount_to_pay
        )

    def _get_domain_amount_to_pay_additional_tax(self):
        return []

    @_debug.perf.timed
    def _generate_locking_attachments(self, options):
        self.check_singleton()
        self._add_attachment(self.type_id.report_id.export_to_pdf(options))

    def _add_attachment(self, file_data):
        self.check_singleton()
        data = file_data["file_content"]
        if isinstance(data, str):
            data = data.encode()
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_data["file_name"],
                "datas": base64.b64encode(data),
                "type": "binary",
                "description": file_data["file_name"],
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        self.attachment_ids = [Command.link(attachment.id)]
        return attachment

    @_debug.perf.timed
    def action_submit(self):
        _debug.lifecycle("action_submit", records=self)
        self.check_singleton()
        self._check_all_branches_allowed()
        return self._proceed_with_submission()

    def _proceed_with_submission(self):
        self._check_failing_checks_in_current_stage()
        self.state = "submitted"
        self.date_submission = fields.Date.context_today(self)
        return self._on_post_submission_event()

    def _on_post_submission_event(self):
        if self.type_id.states_workflow == "generic_state_review_submit":
            return self._mark_completed()

        if self.type_id.states_workflow in (
            "generic_state_only_pay",
            "generic_state_tax_report",
        ):
            return self.action_pay()
        return None

    @_debug.perf.timed
    def action_pay(self):
        _debug.lifecycle("action_pay", records=self)
        self.check_singleton()
        self._check_failing_checks_in_current_stage()
        is_positive_amount = (
            self.amount_to_pay_currency_id.compare_amounts(self.total_amount_to_pay, 0)
            > 0
        )
        if is_positive_amount or self.state == "new":
            return self._get_pay_wizard() or self._action_finalize_payment()
        return self._action_finalize_payment()

    @_debug.perf.timed
    def _action_finalize_payment(self):
        _debug.lifecycle("_action_finalize_payment", records=self)
        self.check_singleton()
        self.state = "paid"
        if self.type_id.states_workflow in (
            "generic_state_only_pay",
            "generic_state_tax_report",
        ):
            return self._mark_completed()
        return None

    ####################################################################################################
    ####  Revert Actions
    ####################################################################################################

    @_debug.perf.timed
    def action_delete(self):
        # Since 19.0, Upgrade the module to have the new view with the confirmaton modal, and call .unlink instead.
        # The permission checks this used to restate are an @api.ondelete hook, so unlink() applies them itself.
        _debug.lifecycle("action_delete", records=self)
        self.unlink()

    @_debug.perf.timed
    def action_archive(self):
        _debug.lifecycle("action_archive", records=self)
        super(
            AccountReturn, self.filtered(lambda record: record.state == "new")
        ).action_archive()

    @_debug.perf.timed
    def action_unarchive(self):
        _debug.lifecycle("action_unarchive", records=self)
        self.check_singleton()
        if self.return_type_category == "account_return":
            domain = [
                ("id", "!=", self.id),
                ("company_id", "=", self.company_id.id),
                ("type_id", "=", self.type_id.id),
                ("date_from", "=", self.date_from),
                ("date_to", "=", self.date_to),
                ("return_type_category", "=", self.return_type_category),
                ("active", "=", True),
            ]
            existing_active_return = self.env["account.return"].search(domain, limit=1)
            if existing_active_return:
                _debug.logic(
                    "unarchive_rejected",
                    tax_return=self,
                    existing=existing_active_return,
                )
                raise UserError(
                    _("An active return already exists for the same period.")
                )
        super().action_unarchive()

    def _reset_checks_for_states(self, states):
        checks_to_reset = self.check_ids.filtered(lambda check: check.state in states)
        checks_to_reset.write(
            {
                "refresh_result": True,
                "approver_ids": False,
                "supervisor_id": False,
            }
        )
        for account_return in checks_to_reset.return_id:
            account_return.message_post(
                body=_("All checks and approvers have been reset")
            )

    @_debug.perf.timed
    def action_reset_tax_return_common(self):
        _debug.lifecycle("action_reset_tax_return_common", records=self)
        self.check_singleton()
        if _debug.logic.enabled and not self.is_tax_return:
            _debug.logic("reset_skipped", tax_return=self, reason="not_tax_return")
        if not self.is_tax_return:
            return True

        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(
                _("Only an Accounting Administrator can reset a tax return")
            )

        # Check if it is the last return locked
        domain = [
            ("company_id", "=", self.company_id.id),
            ("type_id", "=", self.type_id.id),
            ("date_lock", "!=", False),
            ("date_deadline", ">", self.date_deadline),
        ]
        if self.env["account.return"].search_count(domain, limit=1):
            raise UserError(
                _(
                    "You cannot reset this return to new, as another return has been locked at a later date."
                )
            )

        # delete carryover if possible
        if report := self.type_id.report_id:
            if (
                not report.country_id
                or report.country_id == self.company_id.account_fiscal_country_id
            ):
                # Check for locked return
                violated_lock_dates = []
                for company in self.company_ids:
                    violated_lock_dates = company._get_lock_date_violations(
                        self.date_to,
                        fiscalyear=False,
                        sale=False,
                        purchase=False,
                        tax=True,
                        hard=True,
                    )
                    if violated_lock_dates:
                        raise UserError(
                            _(
                                "The operation is refused as it would impact an already issued tax statement. "
                                "Please change the following lock dates to proceed: %(lock_date_info)s.",
                                lock_date_info=self.env[
                                    "res.company"
                                ]._format_lock_dates(violated_lock_dates),
                            )
                        )

            carryover_values = self.env["account.report.external.value"].search(
                [
                    ("carryover_origin_report_line_id", "in", report.line_ids.ids),
                    ("date", "=", self.date_to),
                    ("company_id", "in", self.company_ids.ids),
                ]
            )

            carryover_impacted_period = self.type_id._get_period_boundaries(
                self.company_id, self.date_to + relativedelta(days=1)
            )
            _debug.logic(
                "carryover_values_found",
                tax_return=self,
                report=report,
                carryover=carryover_values,
                impacted_period_end=carryover_impacted_period[1],
            )

            violated_lock_dates = (
                self.company_id._get_lock_date_violations(
                    carryover_impacted_period[1],
                    fiscalyear=False,
                    sale=False,
                    purchase=False,
                    tax=True,
                    hard=True,
                )
                if carryover_values
                else None
            )

            if violated_lock_dates:
                raise UserError(
                    _(
                        "You cannot reset this closing entry to draft, as it would delete carryover values impacting the tax report of a locked period. "
                        "Please change the following lock dates to proceed: %(lock_date_info)s.",
                        lock_date_info=self.env["res.company"]._format_lock_dates(
                            violated_lock_dates
                        ),
                    )
                )

            carryover_values.unlink()

            main_company = self.tax_unit_id.main_company_id or self.company_id
            if (
                report.country_id == main_company.account_fiscal_country_id
                and main_company.tax_lock_date
                and self.date_to <= main_company.tax_lock_date
            ):
                _debug.logic(
                    "tax_lock_date_rolled_back",
                    tax_return=self,
                    company=main_company,
                    old_lock_date=main_company.tax_lock_date,
                    companies=self.company_ids,
                )
                for company in self.company_ids:
                    company.sudo().tax_lock_date = self.date_from + relativedelta(
                        days=-1
                    )

            self.total_amount_to_pay = 0
            self.period_amount_to_pay = 0

        self.date_lock = False
        _debug.logic("tax_return_unlocked", tax_return=self, had_report=bool(report))
        self._reset_common()
        return True

    @_debug.perf.timed
    def action_reset_custom_return(self):
        _debug.lifecycle("action_reset_custom_return", records=self)
        self._reset_common()
        return True

    @_debug.perf.timed
    def action_reset_annual_closing(self):
        _debug.lifecycle("action_reset_annual_closing", records=self)
        self.check_singleton()

        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(
                _("Only an Accounting Administrator can reset an annual closing")
            )

        self._reset_common()
        return True

    @_debug.perf.timed
    def action_reset_2_states(self):
        _debug.lifecycle("action_reset_2_states", records=self)
        self.check_singleton()

        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("Only an Accounting Administrator can reset a return"))

        self._reset_common()
        return True

    def _reset_common(self):
        self._reset_checks_for_states(
            [
                state
                for state, _label in self._fields[
                    self.type_id.states_workflow
                ].selection
            ]
        )
        self.state = "new"
        self._mark_uncompleted()
        self.report_opened_once = False
        self.attachment_ids.unlink()
        self.date_submission = False

        if self.closing_move_ids:
            self.closing_move_ids.action_draft()
            self.closing_move_ids.unlink()

    ####################################################################################################
    ####  Other Actions
    ####################################################################################################
    @_debug.perf.timed
    def action_view_attachments(self):
        _debug.lifecycle("action_view_attachments", records=self)
        action = self.action_view_account_return()
        action["context"]["open_attachments_in_chatter"] = True
        return action

    @_debug.perf.timed
    def action_mark_completed(self):
        _debug.lifecycle("action_mark_completed", records=self)
        self.check_singleton()
        return self._mark_completed()

    def _mark_completed(self):
        self.check_singleton()
        self.is_completed = True
        if self.return_type_category == "audit":
            self.audit_status = "done"
        _debug.logic(
            "completion_marked",
            tax_return=self,
            category=self.return_type_category,
            notify=not self.env.context.get("in_checks_view"),
        )
        if not self.env.context.get("in_checks_view"):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "sticky": False,
                    "message": _("Return Completed"),
                    "next": {
                        "type": "ir.actions.client",
                        "tag": "action_return_refresh",
                        "params": {
                            "return_ids": self.ids,
                        },
                    },
                },
            }
        return None

    @_debug.perf.timed
    def action_mark_uncompleted(self):
        _debug.lifecycle("action_mark_uncompleted", records=self)
        self.check_singleton()
        if not self.is_completed:
            raise UserError(_("You can only unarchive a completed return."))
        self._mark_uncompleted()

    def _mark_uncompleted(self):
        self.check_singleton()
        self.is_completed = False
        if self.return_type_category == "audit":
            self.audit_status = "ongoing"

    @_debug.perf.timed
    def action_export_working_files(self):
        _debug.lifecycle("action_export_working_files", records=self)
        report = self.env.ref("account.trial_balance_report").with_company(
            self.company_id.id
        )
        options = report.get_options(
            {
                "selected_variant_id": report.id,
                "date": {
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "mode": "range",
                    "filter": "custom",
                },
                "show_account": True,
                "show_currency": True,
                "show_last_annotations": True,
                "unfold_all": True,
                "report_title": self.name.strip(),
            }
        )
        return {
            "type": "ir_actions_account_report_download",
            "data": {
                "model": self.env.context.get("model"),
                "options": json.dumps(options),
                "file_generator": "export_to_pdf",
            },
        }

    @_debug.perf.timed
    def action_view_entry(self):
        _debug.lifecycle("action_view_entry", records=self)
        self.check_singleton()
        name = (
            _("Closing Entries")
            if len(self.closing_move_ids) > 1
            else _("Closing Entry")
        )
        return self.closing_move_ids._get_records_action(name=name)

    @_debug.perf.timed
    def action_view_report(self):
        _debug.lifecycle("action_view_report", records=self)
        self.check_singleton()
        if self.has_access("write") and self.state == "reviewed":
            self.report_opened_once = True
        options = self._get_closing_report_options()
        return {
            "type": "ir.actions.client",
            "name": self.type_id.report_id.display_name,
            "tag": "account_report",
            "context": {"report_id": self.type_id.report_id.id},
            "params": {"options": options, "ignore_session": True},
        }

    def _get_closing_report_options(self):
        report = self.type_id.report_id

        date_filter = "custom_return_period"
        periodicity = self.type_id._get_periodicity(self.company_id)
        if periodicity == "fiscalyear" or not self._period_match_periodicity():
            date_filter = "custom"

        options = {
            "date": {
                "date_from": fields.Date.to_string(self.date_from),
                "date_to": fields.Date.to_string(self.date_to),
                "filter": date_filter,
                # use custom period in case of anormal dates
                "mode": "range",
            },
            "selected_variant_id": report.id,
            "sections_source_id": report.id,
            "tax_unit": "company_only" if not self.tax_unit_id else self.tax_unit_id.id,
            "selected_return_type_id": self.type_id.id,
        }
        current_company = self.env.company
        company_ids = self.company_ids.ids
        return (
            report.sudo()
            .with_context(allowed_company_ids=company_ids)
            .with_company(current_company)
            .get_options(previous_options=options)
        )

    def _period_match_periodicity(self):
        aligned_date_from, aligned_date_to = self.type_id._get_period_boundaries(
            self.company_id, self.date_from
        )
        return self.date_from == aligned_date_from and self.date_to == aligned_date_to

    @_debug.perf.timed
    def action_send_email_instructions(self, wizard, template):
        _debug.lifecycle("action_send_email_instructions", records=self)
        self.check_singleton()

        compose_form = self.env.ref("mail.email_compose_message_wizard_form")

        ctx = {
            "default_model": "account.return",
            "default_res_ids": self.ids,
            "default_template_id": template.id if template else False,
            "default_composition_mode": "comment",
            "default_partner_ids": self._get_return_mail_recipients(),
            "mail_notify_author": True,
            "reply_to_force_new": False,
            "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
            "default_account_reports_finalize_payment": True,
        }

        if wizard and "qr_code" in wizard:
            ctx.update(
                {
                    "qr_data": wizard._prepare_b64_qr_data(),
                    "communication": wizard.communication,
                }
            )
        _debug.logic(
            "email_instructions_prepared",
            tax_return=self,
            template=template,
            with_qr="qr_data" in ctx,
            recipients=len(ctx.get("default_partner_ids") or []),
        )

        return {
            "name": template.name if template else "Tax payment",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }

    def _get_return_mail_recipients(self):
        mail = self.env["mail.mail"].search(
            [
                ("model", "=", "account.return"),
                ("res_id", "=", self.id),
                ("record_company_id", "=", self.company_id.id),
            ],
            order="create_date desc",
            limit=1,
        )
        return mail.partner_ids.ids or self.env.user.partner_id.ids

    ####################################################################################################
    ####  Tax Closing
    ####################################################################################################
    @_debug.perf.timed
    def _create_tax_closing_entries(self, options):
        """Create and post one closing move per company of the return.

        :param options: report options
        """
        self.check_singleton()
        self._check_tax_group_configuration_for_tax_closing()

        closing_move_vals = []
        for company in self.company_ids:
            line_ids_vals, tax_group_subtotal = self.sudo()._get_tax_closing_entry(
                company, options
            )
            line_ids_vals += self.sudo()._add_tax_group_closing_items(
                tax_group_subtotal, company
            )
            closing_move_vals.append(
                {
                    "company_id": company.id,  # Important to specify together with the journal, for branches
                    "journal_id": company._get_tax_closing_journal().id,
                    "date": self.date_to,
                    "closing_return_id": self.id,
                    "ref": self.name,
                    "line_ids": line_ids_vals,
                }
            )

        moves = self.env["account.move"].sudo().create(closing_move_vals)
        _debug.pipeline(
            "closing_companies",
            tax_return=self,
            moves=moves,
            company_ids=self.company_ids,
        )
        moves.action_post()

    @_debug.perf.timed
    def _check_tax_group_configuration_for_tax_closing(self):
        """Raise a RedirectWarning informing the user his tax groups are missing configuration,
        redirecting him to the list view of account.tax.group filtered on the report's country.
        """
        self.check_singleton()

        tax_with_incomplete_group_domain = [
            *self.env["account.tax"]._check_company_domain(self.company_ids),
            "|",
            ("tax_group_id.tax_payable_account_id", "=", False),
            ("tax_group_id.tax_receivable_account_id", "=", False),
        ]

        country = self.type_id.report_id.country_id
        if country:
            tax_with_incomplete_group_domain.append(("country_id", "=", country.id))

        if self.env["account.tax"].search(tax_with_incomplete_group_domain, limit=1):
            tax_groups_domain = (
                [("country_id", "in", (False, country.id))] if country else []
            )
            _debug.logic(
                "tax_group_accounts_missing",
                tax_return=self,
                country=country,
            )

            raise RedirectWarning(
                _("Please specify the accounts necessary for the tax closing entry."),
                {
                    "type": "ir.actions.act_window",
                    "name": "Tax groups",
                    "res_model": "account.tax.group",
                    "view_mode": "list",
                    "views": [[False, "list"]],
                    "domain": tax_groups_domain,
                },
                _("Configure accounts"),
            )

    @_debug.perf.timed
    def _get_tax_closing_entry(self, company, options):
        """Compute the tax closing entry.

        :return: the one2many commands balancing the tax accounts for the selected period, and the
            subtotal dictionary used to balance the accounts set per tax group
        :rtype: tuple
        """
        self.env.flush_all()

        company_options = {
            **options,
            "forced_domain": options.get("forced_domain", [])
            + [("company_id", "=", company.id)],
        }

        query = self.type_id.report_id._get_report_query(
            company_options,
            "strict_range",
            domain=self._get_domain_vat_closing_entry_additional(),
        )

        # Check whether it is multilingual, in order to get the translation from the JSON value if present
        tax_name = self.env["account.tax"]._field_to_sql("tax", "name")

        query = SQL(
            """
            SELECT repartition.tax_id as tax_id,
                    tax.tax_group_id as tax_group_id,
                    %(tax_name)s as tax_name,
                    "account_move_line".account_id,
                    COALESCE(SUM("account_move_line".balance), 0) as amount
            FROM account_tax tax, account_tax_repartition_line repartition, %(table_references)s
            WHERE %(search_condition)s
              AND repartition.id = "account_move_line".tax_repartition_line_id
              AND tax.id = repartition.tax_id
              AND repartition.use_in_tax_closing
            GROUP BY tax.tax_group_id, repartition.tax_id, tax.name, "account_move_line".account_id
            """,
            tax_name=tax_name,
            table_references=query.from_clause,
            search_condition=query.where_clause,
        )
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        _debug.perf.count("closing_query_rows", rows=len(results))
        results = self._postprocess_vat_closing_entry_results(
            company, company_options, results
        )
        _debug.pipeline(
            "closing_results_postprocessed",
            tax_return=self,
            company=company,
            rows=len(results),
        )

        tax_group_ids = [r["tax_group_id"] for r in results]
        tax_groups = defaultdict(lambda: defaultdict(list))
        for tg, result in zip(
            self.env["account.tax.group"].browse(tax_group_ids), results, strict=False
        ):
            tax_groups[tg][result.get("tax_id")].append(
                (result.get("tax_name"), result.get("account_id"), result.get("amount"))
            )

        # then loop on previous results to
        #    * add the lines that will balance their sum per account
        #    * make the total per tax group's account triplet
        # (if 2 tax groups share the same 3 accounts, they should consolidate in the vat closing entry)
        move_vals_lines = []
        tax_group_subtotal = defaultdict(float)
        currency = company.currency_id
        for tg, values in tax_groups.items():
            total = 0
            # ignore line that have no property defined on tax group
            if not tg.tax_receivable_account_id or not tg.tax_payable_account_id:
                _debug.logic(
                    "tax_group_skipped",
                    tax_return=self,
                    tax_group=tg,
                    reason="missing_receivable_or_payable_account",
                )
                continue
            for value in values.values():
                for tax_name, account_id, amt in value:
                    # Line to balance
                    move_vals_lines.append(
                        Command.create(
                            {
                                "name": tax_name,
                                "debit": abs(amt) if amt < 0 else 0,
                                "credit": max(0, amt),
                                "account_id": account_id,
                            }
                        )
                    )
                    total += amt

            if not currency.is_zero(total):
                # Add total to correct group
                key = (
                    tg.advance_tax_payment_account_id.id or False,
                    tg.tax_receivable_account_id.id,
                    tg.tax_payable_account_id.id,
                )

                tax_group_subtotal[key] += total
        _debug.pipeline(
            "closing_lines_built",
            tax_return=self,
            company=company,
            tax_groups=len(tax_groups),
            lines=len(move_vals_lines),
            subtotal_keys=len(tax_group_subtotal),
        )

        # If the tax report is completely empty, we add two 0-valued lines, using the first in in and out
        # account id we find on the taxes.
        if not move_vals_lines:
            rep_ln_in = self.env["account.tax.repartition.line"].search(
                [
                    *self.env["account.tax.repartition.line"]._check_company_domain(
                        company
                    ),
                    ("account_id.active", "=", True),
                    ("repartition_type", "=", "tax"),
                    ("document_type", "=", "invoice"),
                    ("tax_id.type_tax_use", "=", "purchase"),
                ],
                limit=1,
            )
            rep_ln_out = self.env["account.tax.repartition.line"].search(
                [
                    *self.env["account.tax.repartition.line"]._check_company_domain(
                        company
                    ),
                    ("account_id.active", "=", True),
                    ("repartition_type", "=", "tax"),
                    ("document_type", "=", "invoice"),
                    ("tax_id.type_tax_use", "=", "sale"),
                ],
                limit=1,
            )

            if rep_ln_out.account_id and rep_ln_in.account_id:
                move_vals_lines = [
                    Command.create(
                        {
                            "name": _("Tax Received Adjustment"),
                            "debit": 0.0,
                            "credit": 0.0,
                            "account_id": rep_ln_out.account_id.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": _("Tax Paid Adjustment"),
                            "debit": 0.0,
                            "credit": 0.0,
                            "account_id": rep_ln_in.account_id.id,
                        }
                    ),
                ]
            _debug.logic(
                "closing_report_empty",
                tax_return=self,
                company=company,
                repartition_in=rep_ln_in,
                repartition_out=rep_ln_out,
                placeholder_lines=len(move_vals_lines),
            )

        return move_vals_lines, tax_group_subtotal

    @_debug.perf.timed
    def _vat_closing_entry_results_rounding(
        self, company, options, results, rounding_accounts, vat_results_summary
    ):
        """
        Apply the rounding from the tax report by adding a line to the end of the query results
        representing the sum of the roundings on each line of the tax report.
        """
        # Ignore if the rounding accounts cannot be found
        if _debug.logic.enabled and (
            not rounding_accounts.get("profit") or not rounding_accounts.get("loss")
        ):
            _debug.logic(
                "rounding_skipped",
                tax_return=self,
                company=company,
                reason="rounding_accounts_missing",
            )
        if not rounding_accounts.get("profit") or not rounding_accounts.get("loss"):
            return results

        total_amount = 0.0
        tax_group_id = None

        for line in results:
            total_amount += line["amount"]
            # The accounts on the tax group ids from the results should be uniform,
            # but we choose the greatest id so that the line appears last on the entry.
            tax_group_id = line["tax_group_id"]

        report = self.env["account.report"].browse(options["report_id"])

        for line in report._get_lines(options):
            model, record_id = report._get_model_info_from_id(line["id"])

            if model != "account.report.line":
                continue

            for (
                operation_type,
                report_line_id,
                column_expression_label,
            ) in vat_results_summary:
                for column in line["columns"]:
                    if (
                        record_id != report_line_id
                        or column["expression_label"] != column_expression_label
                    ):
                        continue

                    # We accept 3 types of operations:
                    # 1) due and 2) deductible - This is used for reports that have lines for the payable vat and
                    # lines for the reclaimable vat.
                    # 3) total - This is used for reports that have a single line with the payable/reclaimable vat.
                    if operation_type in {"due", "total"}:
                        total_amount += column["no_format"]
                    elif operation_type == "deductible":
                        total_amount -= column["no_format"]

        currency = company.currency_id
        total_difference = currency.round(total_amount)

        if not currency.is_zero(total_difference):
            results.append(
                {
                    "tax_name": _("Difference from rounding taxes"),
                    "amount": total_difference * -1,
                    "tax_group_id": tax_group_id,
                    "account_id": rounding_accounts["profit"].id
                    if total_difference < 0
                    else rounding_accounts["loss"].id,
                }
            )
        _debug.logic(
            "rounding_difference_computed",
            tax_return=self,
            company=company,
            total=total_amount,
            difference=total_difference,
            tax_group=tax_group_id,
            rows=len(results),
        )

        return results

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # Override this to, for example, apply a rounding to the lines of the closing entry
        return results

    def _get_domain_vat_closing_entry_additional(self):
        return []

    @_debug.perf.timed
    def _add_tax_group_closing_items(self, tax_group_subtotal, company):
        """Transform the tax_group_subtotal dictionary into the one2many commands balancing the
        tax group accounts of the VAT closing entry.

        :param company: the company whose closing move is being built.
        :rtype: list
        """

        def _add_line(account_id, name, company_currency):
            advance_balance = self.env["account.move.line"]._read_group(
                [
                    ("date", "<=", self.date_to),
                    ("account_id", "=", account_id),
                    ("company_id", "=", company.id),
                    ("parent_state", "=", "posted"),
                ],
                aggregates=["balance:sum"],
            )[0][0]

            # Deduct/Add advance payment
            if not company_currency.is_zero(advance_balance):
                line_ids_vals.append(
                    Command.create(
                        {
                            "name": name,
                            "debit": abs(advance_balance) if advance_balance < 0 else 0,
                            "credit": abs(advance_balance)
                            if advance_balance > 0
                            else 0,
                            "account_id": account_id,
                        }
                    )
                )
            return advance_balance

        currency = company.currency_id
        line_ids_vals = []
        # keep track of already balanced account, as one can be used in several tax group
        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(
                    key[0], _("Balance tax advance payment account"), currency
                )
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(
                    key[1], _("Balance tax current account (receivable)"), currency
                )
                account_already_balanced.append(key[1])

            # Balance on the receivable/payable tax account
            if not currency.is_zero(total):
                line_ids_vals.append(
                    Command.create(
                        {
                            "name": _("Payable tax amount")
                            if total < 0
                            else _("Receivable tax amount"),
                            "debit": max(0, total),
                            "credit": abs(total) if total < 0 else 0,
                            "account_id": key[2] if total < 0 else key[1],
                        }
                    )
                )
        _debug.pipeline(
            "tax_group_closing_items_built",
            tax_return=self,
            company=company,
            subtotal_keys=len(tax_group_subtotal),
            balanced_accounts=len(account_already_balanced),
            lines=len(line_ids_vals),
        )
        return line_ids_vals

    ####################################################################################################
    ####  Checks
    ####################################################################################################

    @_debug.perf.timed
    def _check_failing_checks_in_current_stage(self):
        self.check_singleton()
        domain = [
            ("return_id", "=", self.id),
            ("state", "=", self.state),
            ("result", "in", ("todo", "anomaly")),
        ]
        if self.env["account.return.check"].search_count(domain, limit=1):
            raise UserError(
                _(
                    "Some checks fail in the current stage, please solve them before proceeding."
                )
            )

    @_debug.perf.timed
    def refresh_checks(self):
        """
        Recompute all checks for every return in self of the current state
        """
        # Lock the return records before processing to ensure only one worker can
        # modify them at a time, preventing race conditions in parallel execution.
        locked_returns = self.try_lock_for_update()
        if (
            not self.env["account.return.check"].has_access("write")
            or not locked_returns
        ):
            _debug.logic("refresh_checks_skipped", records=self, locked=locked_returns)
            return

        to_create = []
        to_unlink = self.env["account.return.check"]
        for record in locked_returns:
            if (
                record.company_id not in self.env.companies
            ):  # We do not run checks if the main company is not selected
                continue

            if record._is_check_run_required():
                check_codes_to_ignore = set(
                    record.check_ids.filtered(
                        lambda x, record=record: x.state != record.state
                    ).mapped("code")
                )
                rslt = record._run_checks(check_codes_to_ignore)
                rslt += record._execute_template_checks(check_codes_to_ignore)

                checks_by_code = record.check_ids.grouped(lambda x: x.code)
                codes_refreshed = set()
                for vals in rslt:
                    codes_refreshed.add(vals["code"])
                    if existing_check := checks_by_code.get(vals["code"]):
                        # If a user has updated `result`, we no longer updates its value automatically.
                        if not existing_check.refresh_result:
                            vals.pop("result", None)
                        existing_check.with_user(SUPERUSER_ID).write(vals)
                    else:
                        to_create.append(
                            {**vals, "state": record.state, "return_id": record.id}
                        )

                obsolete_check_codes = checks_by_code.keys() - (
                    codes_refreshed | check_codes_to_ignore
                )
                _debug.logic(
                    "checks",
                    tax_return=record,
                    rslt_count=len(rslt),
                    check_codes_to_ignore_count=len(check_codes_to_ignore),
                    obsolete_check_codes_count=len(obsolete_check_codes),
                )
                if obsolete_check_codes:
                    to_unlink |= record.check_ids.filtered(
                        lambda c, obsolete_check_codes=obsolete_check_codes: (
                            c.code in obsolete_check_codes
                        )
                    )
        if to_create:
            self.env["account.return.check"].with_user(SUPERUSER_ID).create(to_create)
        to_unlink.unlink()

    def _is_check_run_required(self):
        # To override in order to run checks in other custom-made states
        self.check_singleton()
        return self.state == "new"

    @_debug.perf.timed
    def _execute_template_checks(self, codes_to_ignore):
        def filter_template(template):
            return template.code not in codes_to_ignore and (
                not template.country_ids
                or self.company_id.account_fiscal_country_id in template.country_ids
            )

        return_type = self.type_id
        check_templates = self.env["account.return.check.template"].search(
            [
                ("return_type", "=", return_type.id),
                ("cycle", "not in", (self.skipped_check_cycles or "").split(",")),
            ]
        )

        existing_checks_from_template = self.check_ids.filtered(lambda r: r.template_id)
        existing_check_by_template_id = {
            check.template_id: check for check in existing_checks_from_template
        }
        _debug.pipeline(
            "check_templates_found",
            tax_return=self,
            returntype=return_type,
            templates=check_templates,
            existing_from_template=len(existing_check_by_template_id),
            ignored=len(codes_to_ignore),
        )

        vals_list = []

        for template in check_templates.filtered(filter_template):
            action = template.action_id
            vals_dict = {
                "code": template.code,
                "name": template.name,
                "message": template.description,
                "type": template.type,
                "action": False,
            }

            if action:
                action_record = self.env[action.sudo().type].browse(action.sudo().id)
                vals_dict["action"] = action_record._get_action_dict()

            if template not in existing_check_by_template_id:
                vals_dict.update(
                    {
                        "template_id": template.id,
                    }
                )
            elif existing_check_by_template_id[template].type != template.type:
                # If the existing check type does not match we have to reset the result
                vals_dict["result"] = "todo"
                _debug.logic(
                    "check_type_changed_reset",
                    tax_return=self,
                    template=template,
                    new_type=template.type,
                )
                if (
                    existing_check_by_template_id[template].type == "file"
                    and existing_check_by_template_id[template].attachment_ids
                ):
                    existing_check_by_template_id[template].attachment_ids.unlink()

            if template.activity_type:
                current_template_activities = self.activity_ids.filtered(
                    lambda act, template=template: act.summary == template.name
                )
                activities_to_unlink = current_template_activities.filtered(
                    lambda act: act.state != "done"
                )
                activities_kept = current_template_activities - activities_to_unlink
                _debug.logic(
                    "template_activities_synced",
                    template=template,
                    unlinked=activities_to_unlink,
                    kept=activities_kept,
                )
                activities_to_unlink.unlink()
                if not activities_kept:
                    self.activity_schedule(
                        activity_type_id=template.activity_type.id,
                        summary=template.name,
                        note=template.description,
                    )

            if template.type == "check" and template.model:
                ir_model = self.env["ir.model"]._get(template.model)
                model = self.env[template.model]
                domain = []
                if template.domain:
                    domain = ast.literal_eval(template.domain)
                domain = [
                    *domain,
                    ("date", ">=", fields.Date.to_string(self.date_from)),
                    ("date", "<=", fields.Date.to_string(self.date_to)),
                    ("company_id", "in", self.company_ids.ids),
                ]
                entries = model.sudo().search(domain, limit=LIMIT_CHECK_ENTRIES)  # noqa: E8507 - one query per check template; each has its own model and domain
                if entries:
                    if action := template._get_default_check_action_from_model():
                        action["domain"] = [*action.get("domain", []), *domain]
                    else:
                        action = {
                            "type": "ir.actions.act_window",
                            "name": template.name,
                            "view_mode": "list",
                            "res_model": model._name,
                            "domain": domain,
                            "views": [[False, "list"], [False, "form"]],
                        }
                    vals_dict.update(
                        {
                            "action": action,
                            "records_count": len(entries),
                            "records_model": ir_model.id,
                            "result": "anomaly",
                        }
                    )
                else:
                    vals_dict["result"] = "reviewed"
                _debug.logic(
                    "template_check_evaluated",
                    tax_return=self,
                    template=template,
                    model=template.model,
                    entries=len(entries),
                    result=vals_dict.get("result"),
                )

            vals_list.append(vals_dict)

        _debug.pipeline("template_checks_built", tax_return=self, checks=len(vals_list))
        return vals_list

    @_debug.perf.timed
    def _run_checks(self, check_codes_to_ignore):
        """
        To override in l10n for specific checks by type
        """
        self.check_singleton()
        checks = []
        report_country = self.type_id.report_id.country_id
        europe_country_group = self.env.ref("base.europe")
        if report_country.code in europe_country_group.mapped("country_ids.code"):
            checks += self._check_suite_eu_vat_report(check_codes_to_ignore)

        if self.is_tax_return:
            checks += self._check_suite_common_vat_report(check_codes_to_ignore)
        elif self.is_ec_sales_list_return:
            checks += self._check_suite_common_ec_sales_list(check_codes_to_ignore)
        if self.type_external_id == "account.annual_corporate_tax_return_type":
            checks += self._check_suite_annual_closing(check_codes_to_ignore)

        _debug.pipeline(
            "check_suites_run",
            tax_return=self,
            country=report_country,
            tax=self.is_tax_return,
            checks=len(checks),
        )
        return checks

    @_debug.perf.timed
    def _check_suite_common_vat_report(self, check_codes_to_ignore):
        checks = []
        # check company configuration
        if "check_company_data" not in check_codes_to_ignore:
            review_action = {
                "type": "ir.actions.act_window",
                "name": _("Set your company data"),
                "res_model": "res.company",
                "res_id": self.company_id.id,
                "views": [
                    (
                        self.env.ref("account.res_company_form_view_onboarding").id,
                        "form",
                    )
                ],
                "target": "new",
            }
            company = self.company_id
            required_fields = [
                company.vat,
                company.country_id,
                company._phone_get_number().number,
                company.email,
            ]
            invalid_fields_count = sum(1 for field in required_fields if not field)
            _debug.logic(
                "company_data_checked",
                tax_return=self,
                company=company,
                invalid_fields=invalid_fields_count,
            )

            checks.append(
                {
                    "name": _lt("Company data"),
                    "message": _lt(
                        "Missing company details (like VAT number or country) can cause errors in your report, "
                        "such as using the wrong VAT rate, wrongly exempting transactions."
                    ),
                    "code": "check_company_data",
                    "records_count": invalid_fields_count,
                    "action": review_action,
                    "result": "anomaly" if invalid_fields_count else "reviewed",
                }
            )

        if "check_match_all_bank_entries" not in check_codes_to_ignore:
            checks.append(
                self._check_match_all_bank_entries(
                    code="check_match_all_bank_entries",
                    name=_lt("Bank Matching"),
                    message=_lt(
                        "Bank matching isn’t required for VAT returns but helps spot missing bills."
                    ),
                )
            )

        if "check_draft_entries" not in check_codes_to_ignore:
            check_codes_to_ignore.add("check_draft_entries")
            checks.append(
                self._check_draft_entries(
                    code="check_draft_entries",
                    name=_lt("Draft entries"),
                    message=_lt(
                        "Review and post draft invoices and bills in the period, or change their accounting date."
                    ),
                    exclude_entries=True,
                )
            )

        if "check_bills_attachment" not in check_codes_to_ignore:
            domain = [
                ("attachment_ids", "=", False),
                ("move_type", "=", "in_invoice"),
                ("company_id", "in", self.company_ids.ids),
                ("date", "<=", fields.Date.to_string(self.date_to)),
                ("date", ">=", fields.Date.to_string(self.date_from)),
                ("state", "=", "posted"),
            ]
            bills_without_attachments_count = (
                self.env["account.move"]
                .sudo()
                .search_count(domain, limit=LIMIT_CHECK_ENTRIES)
            )
            _debug.logic(
                "bills_without_attachment_counted",
                tax_return=self,
                count=bills_without_attachments_count,
            )

            review_action = {
                "type": "ir.actions.act_window",
                "name": _("Bill Attachments"),
                "view_mode": "list",
                "res_model": "account.move",
                "domain": domain,
                "views": [[False, "list"], [False, "form"]],
            }

            checks.append(
                {
                    "name": _lt("Bill attachments"),
                    "code": "check_bills_attachment",
                    "message": _lt(
                        "Each bill should have its own document attached as a proof in case of audit."
                    ),
                    "records_count": bills_without_attachments_count,
                    "records_model": self.env["ir.model"]._get("account.move").id,
                    "action": review_action
                    if bills_without_attachments_count
                    else None,
                    "result": "anomaly"
                    if bills_without_attachments_count
                    else "reviewed",
                }
            )

        if "check_tax_countries" not in check_codes_to_ignore:
            self.env["account.move"].flush_model()
            self.env["account.fiscal.position"].flush_model()
            self.env["res.partner"].flush_model()
            self.env["res.country.group"].flush_model()

            self.env.cr.execute(
                SQL(
                    """
                SELECT ARRAY_AGG(move.id)
                FROM account_move move
                JOIN account_fiscal_position fpos
                    ON fpos.id = move.fiscal_position_id
                JOIN res_partner partner
                    ON partner.id = move.commercial_partner_id
                WHERE
                    move.state = 'posted'
                    AND move.company_id IN %(company_ids)s
                    AND move.move_type IN %(invoice_types)s
                    AND move.date >= %(date_from)s
                    AND move.date <= %(date_to)s
                    AND (fpos.country_id IS NOT NULL OR fpos.country_group_id IS NOT NULL)
                    AND (fpos.country_id IS NULL OR partner.country_id IS NULL OR fpos.country_id != partner.country_id)
                    AND (
                        fpos.country_group_id IS NULL
                        OR partner.country_id IS NULL
                        OR NOT EXISTS (
                            SELECT 1
                            FROM res_country_res_country_group_rel group_rel
                            WHERE group_rel.res_country_id = partner.country_id
                            AND group_rel.res_country_group_id = fpos.country_group_id
                        )
                    )
                """,
                    company_ids=tuple(self.company_ids.ids),
                    invoice_types=tuple(self.env["account.move"].get_invoice_types()),
                    date_from=fields.Date.to_string(self.date_from),
                    date_to=fields.Date.to_string(self.date_to),
                )
            )

            country_error_move_ids = self.env.cr.fetchone()[0]
            country_error_moves_count = len(country_error_move_ids or [])
            _debug.logic(
                "tax_country_mismatch_counted",
                tax_return=self,
                count=country_error_moves_count,
            )

            review_action = {
                "type": "ir.actions.act_window",
                "view_mode": "list",
                "res_model": "account.move",
                "domain": [("id", "in", country_error_move_ids)],
                "views": [[False, "list"], [False, "form"]],
            }

            checks.append(
                {
                    "name": _lt("Taxes and countries matching"),
                    "code": "check_tax_countries",
                    "message": _lt(
                        "Ensure the taxes on invoices and bills match the customer’s country."
                    ),
                    "records_count": country_error_moves_count,
                    "records_model": self.env["ir.model"]._get("account.move").id,
                    "action": review_action if country_error_move_ids else None,
                    "result": "anomaly" if country_error_move_ids else "reviewed",
                }
            )

        if _debug.logic.enabled:
            _debug.logic(
                "vat_suite_results",
                tax_return=self,
                ignored=len(check_codes_to_ignore),
                results=",".join(f"{c.get('code')}={c.get('result')}" for c in checks),
            )
        return checks

    @_debug.perf.timed
    def _check_suite_annual_closing(self, check_codes_to_ignore):
        def get_unknown_partner_aml_ids(report):
            options = report.get_options({})
            unknown_partner_line = next(
                (
                    line
                    for line in report._get_lines(options)
                    if report._get_model_info_from_id(line["id"])
                    == ("res.partner", None)
                ),
                None,
            )
            aml_ids = []
            if unknown_partner_line:
                options["unfolded_lines"] = [unknown_partner_line["id"]]
                aml_ids = [
                    report._get_res_id_from_line_id(line["id"], "account.move.line")
                    for line in report._get_lines(options)
                    if line.get("parent_id") == unknown_partner_line["id"]
                ]
            return aml_ids

        def has_overdue_aged_balance(report, older_expr):
            options = report.get_options(
                {"aging_interval": 15}
            )  # 15-day intervals so amounts aged over 60 fall under 'Older' column
            expression_totals = report._compute_expression_totals_for_each_column_group(
                older_expr, options
            )
            expr_value = next(iter(expression_totals.values()), {}).get(older_expr, {})
            return expr_value.get("value")

        checks = []
        if "check_bank_reconcile" not in check_codes_to_ignore:
            checks.append(
                self._check_match_all_bank_entries(
                    code="check_bank_reconcile",
                    name=_lt("Bank Reconciliation"),
                    message=_lt(
                        "Reconcile all bank account transactions up to year-end."
                    ),
                )
            )

        if "check_draft_entries" not in check_codes_to_ignore:
            checks.append(
                self._check_draft_entries(
                    code="check_draft_entries",
                    name=_lt("No draft entries"),
                    message=_lt(
                        "Review and post draft invoices, bills and entries in the period, or change their accounting date."
                    ),
                )
            )

        if "check_unkown_partner_receivables" not in check_codes_to_ignore:
            receivable_report = self.env.ref("account.aged_receivable_report")
            aml_ids = self.env["account.move.line"].browse(
                get_unknown_partner_aml_ids(receivable_report)
            )
            _debug.logic(
                "unknown_partner_receivables_found",
                tax_return=self,
                lines=len(aml_ids),
            )
            checks.append(
                {
                    "name": _lt("Aged receivables per partner"),
                    "message": _lt("Review receivables without a partner."),
                    "code": "check_unkown_partner_receivables",
                    "action": aml_ids._get_records_action() if aml_ids else None,
                    "result": "anomaly" if aml_ids else "reviewed",
                }
            )

        if "check_overdue_receivables" not in check_codes_to_ignore:
            receivable_report = self.env.ref("account.aged_receivable_report")
            older_expr = self.env.ref("account.aged_receivable_line_period5")
            has_overdue_receivables = has_overdue_aged_balance(
                receivable_report, older_expr
            )
            _debug.logic(
                "overdue_receivables_evaluated",
                tax_return=self,
                older_value=has_overdue_receivables,
            )
            action = None
            if has_overdue_receivables:
                action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                    "account.action_account_report_ar"
                )
                action["params"] = {"ignore_session": True}
            checks.append(
                {
                    "name": _lt("Overdue receivables"),
                    "message": _lt(
                        "Review overdue receivables aged over 60 days and assess the need for an allowance for doubtful accounts or expected credit loss provision, as per IFRS 9 guidelines."
                    ),
                    "code": "check_overdue_receivables",
                    "action": action,
                    "result": "anomaly" if has_overdue_receivables else "reviewed",
                }
            )

        if "check_total_receivables" not in check_codes_to_ignore:
            checks.append(
                {
                    "name": _lt("Total Receivables"),
                    "message": _lt(
                        "Verify that the total aged receivables equals the customer account balance."
                    ),
                    "code": "check_total_receivables",
                    "result": "reviewed",
                }
            )

        if "check_unkown_partner_payables" not in check_codes_to_ignore:
            payable_report = self.env.ref("account.aged_payable_report")
            aml_ids = self.env["account.move.line"].browse(
                get_unknown_partner_aml_ids(payable_report)
            )
            _debug.logic(
                "unknown_partner_payables_found",
                tax_return=self,
                lines=len(aml_ids),
            )
            checks.append(
                {
                    "name": _lt("Aged payables per partner"),
                    "message": _lt("Review payables without a partner."),
                    "code": "check_unkown_partner_payables",
                    "action": aml_ids._get_records_action() if aml_ids else None,
                    "result": "anomaly" if aml_ids else "reviewed",
                }
            )

        if "check_overdue_payables" not in check_codes_to_ignore:
            payable_report = self.env.ref("account.aged_payable_report")
            older_expr = self.env.ref("account.aged_payable_line_period5")
            has_overdue_payables = has_overdue_aged_balance(payable_report, older_expr)
            _debug.logic(
                "overdue_payables_evaluated",
                tax_return=self,
                older_value=has_overdue_payables,
            )
            action = None
            if has_overdue_payables:
                action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                    "account.action_account_report_ap"
                )
                action["params"] = {"ignore_session": True}
            checks.append(
                {
                    "name": _lt("Overdue payables"),
                    "message": _lt(
                        "Review overdue payables aged over 60 days and assess the need for an allowance for uncertain liabilities."
                    ),
                    "code": "check_overdue_payables",
                    "action": action,
                    "result": "anomaly" if has_overdue_payables else "reviewed",
                }
            )

        if "check_total_payables" not in check_codes_to_ignore:
            checks.append(
                {
                    "name": _lt("Total payables"),
                    "message": _lt(
                        "Verify that the total aged payables equals the vendor account balance."
                    ),
                    "code": "check_total_payables",
                    "result": "reviewed",
                }
            )

        if "check_deferred_entries" not in check_codes_to_ignore:
            domain = [
                ("company_id", "in", self.company_ids.ids),
                ("date", "<=", fields.Date.to_string(self.date_to)),
                ("date", ">=", fields.Date.to_string(self.date_from)),
                ("deferred_original_move_ids", "!=", False),
            ]
            deferred_entries_count = (
                self.env["account.move"]
                .sudo()
                .search_count(domain, limit=LIMIT_CHECK_ENTRIES)
            )
            _debug.logic(
                "deferred_entries_counted",
                tax_return=self,
                count=deferred_entries_count,
                check_added=not deferred_entries_count,
            )
            if not deferred_entries_count:
                checks.append(
                    {
                        "name": _lt("Deferred Entries"),
                        "message": _lt(
                            "Odoo manages your deferred entries automatically. No deferred entries were found for this period. Ensure your start and end dates are correctly set on your bills and invoices."
                        ),
                        "code": "check_deferred_entries",
                        "records_count": deferred_entries_count,
                        "records_model": self.env["ir.model"]._get("account.move").id,
                        "result": "todo",
                    }
                )

        if "manual_adjustments" not in check_codes_to_ignore:
            checks.append(
                {
                    "name": _lt("Manual Adjustments"),
                    "message": _lt(
                        "Complete any necessary manual adjustments and internal checks."
                    ),
                    "code": "manual_adjustments",
                    "result": "todo",
                }
            )

        if "earnings_allocation" not in check_codes_to_ignore:
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "account.action_account_report_bs"
            )
            action["params"] = {
                "ignore_session": True,
            }
            checks.append(
                {
                    "name": _lt("Earnings Allocation"),
                    "message": _lt(
                        "After adjustements, transfer the undistributed Profits/Losses to an equity account."
                    ),
                    "code": "earnings_allocation",
                    "action": action,
                    "result": "todo",
                }
            )

        if _debug.logic.enabled:
            _debug.logic(
                "annual_closing_suite_results",
                tax_return=self,
                ignored=len(check_codes_to_ignore),
                results=",".join(f"{c.get('code')}={c.get('result')}" for c in checks),
            )
        return checks

    @_debug.perf.timed
    def _check_suite_eu_vat_report(self, check_codes_to_ignore):
        checks = []
        self._generic_vies_vat_check(check_codes_to_ignore, checks)
        check_codes_to_ignore.add("check_partner_vies")
        return checks

    @_debug.perf.timed
    def _generic_vies_vat_check(self, check_codes_to_ignore, checks):
        is_account_vat_installed = (
            "account_vat" in self.env["ir.module.module"]._get_installed_module_ids()
        )
        use_vies = is_account_vat_installed and self.company_id.vat_check_vies
        _debug.logic(
            "vies_check_mode",
            tax_return=self,
            account_vat_installed=is_account_vat_installed,
            use_vies=bool(use_vies),
            ignored="check_partner_vies" in check_codes_to_ignore,
        )
        if "check_partner_vies" not in check_codes_to_ignore and use_vies:
            european_country_group = self.env.ref("base.europe")
            invalid_vies_partners = (
                self.env["account.move"]
                .sudo()
                ._read_group(
                    domain=[
                        (
                            "partner_id.country_id",
                            "in",
                            european_country_group.country_ids.ids,
                        ),
                        (
                            "partner_id.country_id",
                            "!=",
                            self.company_id.account_fiscal_country_id.id,
                        ),
                        ("partner_id.vies_valid", "=", False),
                        ("company_id", "in", self.company_ids.ids),
                        ("date", "<=", fields.Date.to_string(self.date_to)),
                        ("date", ">=", fields.Date.to_string(self.date_from)),
                        ("fiscal_position_id.vat_required", "=", True),
                    ],
                    aggregates=["partner_id:recordset"],
                )[0][0]
            )

            invalid_vies_partners_count = len(invalid_vies_partners)
            _debug.logic(
                "vies_invalid_partners_found",
                tax_return=self,
                partner=invalid_vies_partners,
            )
            checks.append(
                {
                    "name": _lt("Valid VAT Numbers"),
                    "code": "check_partner_vies",
                    "message": _lt(
                        """All customer VAT numbers are valid under VIES."""
                    ),
                    "state": "new",
                    "records_count": invalid_vies_partners_count,
                    "records_model": self.env["ir.model"]._get("res.partner").id,
                    "action": (
                        invalid_vies_partners._get_records_action(
                            name=self.env._("Valid VAT Numbers")
                        )
                        if invalid_vies_partners_count
                        else None
                    ),
                    "result": "anomaly" if invalid_vies_partners_count else "reviewed",
                }
            )

    @_debug.perf.timed
    def _check_suite_common_ec_sales_list(self, check_codes_to_ignore):
        checks = []

        if (
            "goods_service_classification" not in check_codes_to_ignore
            or "reverse_charge_mentioned" not in check_codes_to_ignore
        ):
            options = self._get_closing_report_options()

            tax_criterium_ids = (
                options["sales_report_taxes"]["goods"]
                + options["sales_report_taxes"]["triangular"]
                + options["sales_report_taxes"]["services"]
            )
            if options["sales_report_taxes"].get("use_taxes_instead_of_tags"):
                tax_criterium = ("tax_ids", "in", tax_criterium_ids)
            else:
                tax_criterium = ("tax_tag_ids", "in", tax_criterium_ids)
            _debug.logic(
                "ec_sales_tax_criterium_chosen",
                tax_return=self,
                field=tax_criterium[0],
                criteria=len(tax_criterium_ids),
            )

            ec_sales_aml_domain = [
                *self.type_id.report_id._get_domain_options(options, "strict_range"),
                tax_criterium,
            ]

            if "goods_service_classification" not in check_codes_to_ignore:
                checks.append(
                    {
                        "name": _lt("Goods and services classification"),
                        "message": _lt(
                            "Review the tax code and ensure each transaction is correctly classified as a supply of goods or services."
                        ),
                        "code": "goods_service_classification",
                        "result": "todo",
                        "action": {
                            "type": "ir.actions.act_window",
                            "name": _("Journal Items"),
                            "res_model": "account.move.line",
                            "domain": ec_sales_aml_domain,
                            "views": [(False, "list")],
                        },
                    }
                )

            if "reverse_charge_mentioned" not in check_codes_to_ignore:
                checks.append(
                    {
                        "name": _lt("Reverse charge mention"),
                        "message": _lt(
                            'Make sure the "Reverse Charge" mention appears on all invoices.'
                        ),
                        "code": "reverse_charge_mentioned",
                        "result": "todo",
                        "action": {
                            "type": "ir.actions.act_window",
                            "name": _("Invoices"),
                            "res_model": "account.move",
                            "domain": [("line_ids", "any", ec_sales_aml_domain)],
                            "views": [(False, "list"), (False, "form")],
                        },
                    }
                )

        if any(
            code not in check_codes_to_ignore
            for code in ("eu_cross_border", "no_partners_without_vat")
        ):
            warnings = {}
            custom_handler = self.env[
                self.type_id.report_id._get_custom_handler_model()
            ]
            options = self._get_closing_report_options()
            partner_results = custom_handler._query_partners(
                self.type_id.report_id, options, warnings
            )

            if "eu_cross_border" not in check_codes_to_ignore:
                cross_border_failure = (
                    "account.sales_report_warning_non_ec_country" in warnings
                    or "account.sales_report_warning_same_country" in warnings
                )
                _debug.logic(
                    "eu_cross_border_evaluated",
                    tax_return=self,
                    failure=cross_border_failure,
                    warnings=len(warnings),
                )

                cross_border_action = False
                if cross_border_failure:
                    options["same_country_warning"] = self.company_id.country_id.code
                    same_country_action = custom_handler.get_warning_act_window(
                        options, {"type": "same_country", "model": "partner"}
                    )
                    non_ec_country_action = custom_handler.get_warning_act_window(
                        options, {"type": "non_ec_country", "model": "partner"}
                    )
                    cross_border_action = {
                        **same_country_action,
                        "name": _("Partners in Wrong Country"),
                        "domain": [
                            "|",
                            *same_country_action["domain"],
                            *non_ec_country_action["domain"],
                        ],
                    }

                checks.append(
                    {
                        "name": _lt("Only intra-EU customers"),
                        "message": _lt(
                            "Exclude any domestic or extra-EU sales from the EC Sales List."
                        ),
                        "code": "eu_cross_border",
                        "result": "anomaly" if cross_border_failure else "reviewed",
                        "action": cross_border_action,
                    }
                )

            if "no_partners_without_vat" not in check_codes_to_ignore:
                no_vat_partners = self.env["res.partner"].browse(
                    partner.id
                    for partner, _partner_result in partner_results
                    if not partner.vat
                )
                _debug.logic(
                    "partners_without_vat_found",
                    tax_return=self,
                    partner=no_vat_partners,
                )
                checks.append(
                    {
                        "name": _lt("VAT Numbers"),
                        "message": _lt("All customers have a VAT number."),
                        "code": "no_partners_without_vat",
                        "result": "anomaly" if no_vat_partners else "reviewed",
                        "action": (
                            no_vat_partners._get_records_action(
                                name=self.env._("Partners without VAT")
                            )
                            if no_vat_partners
                            else None
                        ),
                    }
                )

        self._generic_vies_vat_check(check_codes_to_ignore, checks)

        if _debug.logic.enabled:
            _debug.logic(
                "ec_sales_suite_results",
                tax_return=self,
                ignored=len(check_codes_to_ignore),
                results=",".join(f"{c.get('code')}={c.get('result')}" for c in checks),
            )
        return checks

    @_debug.perf.timed
    def _check_match_all_bank_entries(self, code, name, message):
        domain = [
            ("is_reconciled", "=", False),
            ("state", "!=", "cancel"),
            ("company_id", "in", self.company_ids.ids),
            ("date", "<=", fields.Date.to_string(self.date_to)),
            ("date", ">=", fields.Date.to_string(self.date_from)),
        ]

        unreconciled_bank_entries_count = (
            self.env["account.bank.statement.line"]
            .sudo()
            .search_count(domain, limit=LIMIT_CHECK_ENTRIES)
        )
        _debug.logic(
            "unreconciled_bank_entries_counted",
            tax_return=self,
            code=code,
            count=unreconciled_bank_entries_count,
            capped=unreconciled_bank_entries_count >= LIMIT_CHECK_ENTRIES,
        )

        review_action = {
            "type": "ir.actions.act_window",
            "name": str(
                name
            ),  # If it is _lt, we need to stringify it because it cannot be json dumped
            "view_mode": "list",
            "res_model": "account.bank.statement.line",
            "domain": domain,
            "views": [[False, "kanban"]],
        }

        return {
            "name": name,
            "message": message,
            "code": code,
            "records_count": unreconciled_bank_entries_count,
            "records_model": self.env["ir.model"]
            ._get("account.bank.statement.line")
            .id,
            "action": review_action if unreconciled_bank_entries_count else None,
            "result": "anomaly" if unreconciled_bank_entries_count else "reviewed",
        }

    @_debug.perf.timed
    def action_view_account_return(self):
        _debug.lifecycle("action_view_account_return", records=self)
        self.check_singleton()
        if not self.check_ids:
            self.refresh_checks()

        return {
            "type": "ir.actions.act_window",
            "name": _("Tax Return"),
            "res_model": "account.return.check",
            "view_mode": "kanban",
            "context": {
                "active_model": self._name,
                "active_id": self.id,
                "active_ids": [self.id],
                "account_return_view_id": self.env.ref(
                    "account.account_return_kanban_view"
                ).id,
                "max_number_opened_groups": 100000,
                "open_attachments_in_chatter": True,
            },
            "domain": [["return_id", "=", self.id]],
            "views": [
                (
                    self.env.ref("account.account_return_check_kanban_view").id,
                    "kanban",
                )
            ],
        }

    @_debug.perf.timed
    def _check_draft_entries(self, code, name, message, exclude_entries=False):
        domain = [
            ("state", "=", "draft"),
            ("company_id", "in", self.company_ids.ids),
            ("date", "<=", fields.Date.to_string(self.date_to)),
            ("date", ">=", fields.Date.to_string(self.date_from)),
        ]
        if exclude_entries:
            domain += [("move_type", "!=", "entry")]
        draft_entries_count = (
            self.env["account.move"]
            .sudo()
            .search_count(domain, limit=LIMIT_CHECK_ENTRIES)
        )
        _debug.logic(
            "draft_entries_counted",
            tax_return=self,
            code=code,
            count=draft_entries_count,
            capped=draft_entries_count >= LIMIT_CHECK_ENTRIES,
            invoices_only=exclude_entries,
        )

        review_action = {
            "type": "ir.actions.act_window",
            "name": str(
                name
            ),  # If it is _lt, we need to stringify it because it cannot be json dumped
            "view_mode": "list",
            "res_model": "account.move",
            "domain": domain,
            "views": [
                [self.env.ref("account.view_draft_entries_tree").id, "list"],
                [False, "form"],
            ],
        }

        return {
            "name": name,
            "code": code,
            "message": message,
            "records_count": draft_entries_count,
            "records_model": self.env["ir.model"]._get("account.move").id,
            "action": review_action if draft_entries_count else None,
            "result": "anomaly" if draft_entries_count else "reviewed",
        }

    def get_kanban_view_and_search_view_id(self):
        if self.return_type_category == "audit":
            kanban_view_xml_id = "account.account_audit_kanban_view"
            search_view_xml_id = "account.account_audit_search_view"
        else:
            kanban_view_xml_id = "account.account_return_kanban_view"
            search_view_xml_id = "account.account_return_search_view"
        return (
            self.env.ref(kanban_view_xml_id).id,
            self.env.ref(search_view_xml_id).id,
        )

    @api.model
    def _get_nth_working_day(self, from_date, n):
        """Return the Nth working day (Monday to Friday) starting from a given date.

        :param from_date: the start date, included in the count
        :param n: rank of the working day to find, 1 being the first one on or after from_date
        :return: the date of the Nth working day
        :rtype: datetime.date
        :raises UserError: if n is not strictly positive
        """

        def is_working_day(day):
            return day.isoweekday() <= 5

        if n <= 0:
            raise UserError(self.env._("n must be a positive integer."))

        current_date = from_date
        n -= int(is_working_day(current_date))
        while n > 0:
            current_date += relativedelta(days=1)
            n -= int(is_working_day(current_date))
        return current_date
