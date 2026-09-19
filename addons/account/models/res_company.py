from collections import defaultdict
from datetime import date, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import LockError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, date_utils, format_list
from odoo.tools.misc import format_date

from odoo.addons.account.models.account_move import MAX_HASH_VERSION

_debug = DebugLog(__name__)


PEPPOL_DEFAULT_COUNTRIES = [
    "AT",
    "BE",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GR",
    "IE",
    "IS",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
]

INTEGRITY_HASH_BATCH_SIZE = 1000

PEPPOL_MAILING_COUNTRIES = [
    "BE",
    "LU",
    "NL",
    "SE",
    "NO",
]

PEPPOL_LIST = PEPPOL_DEFAULT_COUNTRIES + [
    "AD",
    "AL",
    "BA",
    "BG",
    "BL",
    "GB",
    "GF",
    "GP",
    "HR",
    "HU",
    "LI",
    "MC",
    "ME",
    "MF",
    "MK",
    "MQ",
    "NC",
    "PF",
    "PM",
    "RE",
    "RS",
    "SK",
    "SM",
    "TF",
    "TR",
    "VA",
    "WF",
    "YT",
]


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mixin.mail.thread"]

    account_config_id = fields.Many2one(
        comodel_name="account.config",
        compute="_compute_account_config_id",
        search="_search_account_config_id",
    )
    account_enabled_tax_country_ids = fields.Many2many(
        related="account_config_id.account_enabled_tax_country_ids"
    )
    company_vat_placeholder = fields.Char(
        related="account_config_id.company_vat_placeholder"
    )

    def _search_account_config_id(self, operator, value):
        return self._search_config_link("account.config", operator, value)

    def _compute_account_config_id(self):
        configs = self.env["account.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.account_config_id = by_company.get(company.id, False)

    def get_next_batch_payment_communication(self):
        self.check_singleton()
        company_sudo = self.sudo()
        if not company_sudo.account_config_id.batch_payment_sequence_id:
            company_sudo.account_config_id.batch_payment_sequence_id = (
                self.env["ir.sequence"]
                .sudo()
                .create(
                    {
                        "name": _("Group Payments Number Sequence"),
                        "implementation": "no_gap",
                        "padding": 5,
                        "use_date_range": True,
                        "company_id": self.id,
                        "prefix": "GROUP/%(year)s/",
                    }
                )
            )
        return company_sudo.account_config_id.batch_payment_sequence_id.next_by_id()

    @api.depends(
        "account_config_id.account_fiscal_country_id",
        "account_config_id.fiscal_position_ids.foreign_vat",
        "account_config_id.fiscal_position_ids.country_id",
    )
    def _initiate_account_onboardings(self):
        account_onboarding_routes = [
            "account_dashboard",
        ]
        onboardings = (
            self.env["onboarding.onboarding"]
            .sudo()
            .search([("route_name", "in", account_onboarding_routes)])
        )
        for company in self:
            onboardings.with_company(company)._search_or_create_progress()

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
        companies = super().create(vals_list)
        for company in companies:
            if root_template := company.root_id.account_config_id.chart_template:
                _debug.pipeline(
                    "created_under_root_template_chart",
                    company=company,
                    root_template=root_template,
                )

                def try_loading(company=company, root_template=root_template):
                    self.env["account.chart.template"]._load(
                        root_template,
                        company,
                        install_demo=False,
                    )

                self.env.cr.precommit.add(try_loading)
        companies._set_category_defaults()
        return companies

    @staticmethod
    def get_new_account_code(current_code, old_prefix, new_prefix):
        digits = len(current_code)
        tail = current_code.removeprefix(old_prefix).lstrip("0")
        return new_prefix + tail.rjust(digits - len(new_prefix), "0")

    def reflect_code_prefix_change(self, old_code, new_code):
        self.check_singleton()
        if not old_code or new_code == old_code:
            return
        accounts = (
            self.env["account.account"]
            .with_company(self)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self),
                    ("code", "=like", old_code + "%"),
                    ("account_type", "in", ("asset_cash", "liability_credit_card")),
                ],
                order="code asc",
            )
        )
        for account in accounts:
            account.write(
                {"code": self.get_new_account_code(account.code, old_code, new_code)}
            )

    def _get_unreconciled_statement_lines_redirect_action(
        self, unreconciled_statement_lines
    ):
        action = {
            "name": _("Unreconciled Transactions"),
            "type": "ir.actions.act_window",
            "res_model": "account.bank.statement.line",
            "context": {"create": False},
        }
        if len(unreconciled_statement_lines) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": unreconciled_statement_lines.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", unreconciled_statement_lines.ids)],
                }
            )
        return action

    def _get_domain_unreconciled_statement_lines(self, last_date):
        return [
            ("company_id", "child_of", self.ids),
            ("is_reconciled", "=", False),
            ("date", "<=", last_date),
            ("move_id.state", "in", ("draft", "posted")),
        ]

    def _get_soft_lock_date_exception(self, company, soft_lock_date_field):
        return self.env["account.lock_exception"].search(
            [
                ("state", "=", "active"),
                "|",
                ("user_id", "=", False),
                ("user_id", "=", self.env.user.id),
                (
                    soft_lock_date_field,
                    "<",
                    company.account_config_id[soft_lock_date_field],
                ),
                ("company_id", "=", company.id),
            ],
            order="lock_date asc NULLS FIRST",
            limit=1,
        )

    def _get_user_lock_date(self, soft_lock_date_field, ignore_exceptions=False):
        self.check_singleton()
        soft_lock_date = date.min
        for company in self.with_context(active_test=False).sudo().parent_ids:
            if company.account_config_id[soft_lock_date_field]:
                if ignore_exceptions:
                    exception = None
                else:
                    exception = self._get_soft_lock_date_exception(
                        company, soft_lock_date_field
                    )
                if exception:
                    soft_lock_date = max(
                        soft_lock_date, exception[soft_lock_date_field] or date.min
                    )
                else:
                    soft_lock_date = max(
                        soft_lock_date, company.account_config_id[soft_lock_date_field]
                    )
        _debug.logic(
            "user_lock_date_resolved",
            company=self,
            field=soft_lock_date_field,
            lock_date=soft_lock_date,
            ignore_exceptions=ignore_exceptions,
        )
        return soft_lock_date

    def _get_user_fiscal_lock_date(self, journal, ignore_exceptions=False):
        self.check_singleton()
        company = self.with_context(ignore_exceptions=ignore_exceptions)
        lock = max(
            company.account_config_id.user_fiscalyear_lock_date,
            company.account_config_id.user_hard_lock_date,
        )
        if journal.type == "sale":
            lock = max(company.account_config_id.user_sale_lock_date, lock)
        elif journal.type == "purchase":
            lock = max(company.account_config_id.user_purchase_lock_date, lock)
        return lock

    def _get_violated_soft_lock_date(self, soft_lock_date_field, accounting_date):
        if not self:
            return None
        self.check_singleton()
        user_lock_date_field = f"user_{soft_lock_date_field}"
        regular_lock_date = self.account_config_id.with_context(ignore_exceptions=True)[
            user_lock_date_field
        ]
        if accounting_date > regular_lock_date:
            return None
        user_lock_date = self.account_config_id.with_context(ignore_exceptions=False)[
            user_lock_date_field
        ]
        return None if accounting_date > user_lock_date else user_lock_date

    @_debug.perf.timed
    def _get_lock_date_violations(
        self,
        accounting_date,
        fiscalyear=True,
        sale=True,
        purchase=True,
        tax=True,
        hard=True,
    ):
        self.check_singleton()
        locks = []

        if not accounting_date:
            return locks

        soft_lock_date_fields_to_check = [
            ("fiscalyear_lock_date", fiscalyear),
            ("sale_lock_date", sale),
            ("purchase_lock_date", purchase),
            ("tax_lock_date", tax),
        ]
        for field, to_check in soft_lock_date_fields_to_check:
            if not to_check:
                continue
            violated_date = self._get_violated_soft_lock_date(field, accounting_date)
            if violated_date:
                locks.append((violated_date, field))

        if hard:
            hard_lock_date = self.account_config_id.user_hard_lock_date
            if accounting_date <= hard_lock_date:
                locks.append((hard_lock_date, "hard_lock_date"))

        if _debug.logic.enabled and locks:
            _debug.logic(
                "lock_dates_violated",
                company=self,
                accounting_date=accounting_date,
                locks=locks,
            )
        return locks

    @api.model
    def _format_lock_dates(self, lock_dates):
        field_labels = self.env["account.config"].fields_get(
            {field for _date, field in lock_dates}, ["string"]
        )
        return format_list(
            self.env,
            [
                f"{field_labels[field]['string']} ({format_date(self.env, lock_date)})"
                for lock_date, field in sorted(lock_dates)
            ],
        )

    def _get_violated_lock_dates(self, accounting_date, has_tax, journal):
        locks = self._get_lock_date_violations(
            accounting_date,
            fiscalyear=True,
            sale=(journal and journal.type == "sale"),
            purchase=(journal and journal.type == "purchase"),
            tax=has_tax,
            hard=True,
        )
        locks.sort()
        return locks

    def write(self, vals):
        if "currency_id" in vals:
            for company in self:
                if (
                    vals["currency_id"] != company.currency_id.id
                    and company.root_id._existing_accounting()
                ):
                    raise UserError(
                        _(
                            "You cannot change the currency of the company since some journal items already exist"
                        )
                    )
        return super().write(vals)

    @api.model
    def setting_init_bank_account_action(self):
        view_id = self.env.ref("account.setup_bank_account_wizard").id
        context = {"dialog_size": "medium", **self.env.context}
        return {
            "type": "ir.actions.act_window",
            "name": _("Setup Bank Account"),
            "res_model": "account.setup.bank.manual.config",
            "target": "new",
            "view_mode": "form",
            "views": [[view_id, "form"]],
            "context": context,
        }

    @api.model
    def setting_init_credit_card_account_action(self):
        view_id = self.env.ref("account.setup_credit_card_account_wizard").id
        context = {"dialog_size": "medium", **self.env.context}
        return {
            "type": "ir.actions.act_window",
            "name": _("Setup Credit Card Account"),
            "res_model": "account.setup.bank.manual.config",
            "target": "new",
            "view_mode": "form",
            "views": [[view_id, "form"]],
            "context": context,
        }

    def _prepare_default_opening_move_values(self):
        self.check_singleton()
        default_journal = self.env["account.journal"].search(
            domain=[
                *self.env["account.journal"]._check_company_domain(self),
                ("type", "=", "general"),
            ],
            limit=1,
        )

        if not default_journal:
            raise UserError(
                _(
                    "Please install a chart of accounts or create a miscellaneous journal before proceeding."
                )
            )

        return {
            "ref": _("Opening Journal Entry"),
            "company_id": self.id,
            "journal_id": default_journal.id,
            "date": (
                self.account_config_id.account_opening_date
                or fields.Date.start_of(fields.Date.today(), "year")
            )
            - timedelta(days=1),
        }

    def opening_move_posted(self):
        return (
            bool(self.account_config_id.account_opening_move_id)
            and self.account_config_id.account_opening_move_id.state == "posted"
        )

    @_debug.perf.timed
    def get_unaffected_earnings_account(self):
        unaffected_earnings_type = "equity_unaffected"
        account = (
            self.env["account.account"]
            .with_company(self)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self),
                    ("account_type", "=", unaffected_earnings_type),
                ],
                limit=1,
            )
        )
        _debug.logic(
            "unaffected_earnings_resolved",
            company=self,
            account=account,
            found=bool(account),
        )
        if account:
            return account
        used_codes = set(
            self.env["account.account"]
            .with_company(self)
            .with_context(active_test=False)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self),
                    ("code", "=like", "9%"),
                ]
            )
            .mapped("code")
        )
        code = 999999
        while str(code) in used_codes:
            code -= 1
        _debug.logic(
            "unaffected_earnings_created",
            company=self,
            code=code,
            used_codes=len(used_codes),
        )
        return (
            self.env["account.account"]
            .with_company(self)
            ._load_records(
                [
                    {
                        "xml_id": f"account.{self.id!s}_unaffected_earnings_account",
                        "values": {
                            "code": str(code),
                            "name": _("Profit or Loss Appropriation"),
                            "account_type": unaffected_earnings_type,
                            "company_ids": [Command.link(self.id)],
                        },
                        "noupdate": True,
                    }
                ]
            )
        )

    @staticmethod
    def _plan_opening_move_lines(
        to_update,
        balancing_account,
        existing_lines,
        initial_balance,
        is_zero,
        amount_currency_of,
        currency_id_of,
        opening_name,
        balancing_name,
    ):
        commands = []
        open_balance = initial_balance

        def emit(account, side, balance, balancing):
            nonlocal open_balance
            lines = existing_lines.get((account, side)) or []
            amount_currency = (
                balance if balancing else amount_currency_of(account, balance)
            )
            open_balance += balance
            if is_zero(balance):
                for line in lines:
                    open_balance -= line.balance
                    commands.append(Command.delete(line.id))
            elif lines:
                line_to_update = lines[0]
                open_balance -= line_to_update.balance
                commands.append(
                    Command.update(
                        line_to_update.id,
                        {"balance": balance, "amount_currency": amount_currency},
                    )
                )
                for line in lines[1:]:
                    open_balance -= line.balance
                    commands.append(Command.delete(line.id))
            else:
                commands.append(
                    Command.create(
                        {
                            "name": balancing_name if balancing else opening_name,
                            "account_id": account.id,
                            "balance": balance,
                            "amount_currency": amount_currency,
                            "currency_id": currency_id_of(account),
                        }
                    )
                )

        for account, (debit, credit) in to_update.items():
            if debit is not None:
                emit(account, "debit", debit, False)
            if credit is not None:
                emit(account, "credit", -credit, False)
        _debug.pipeline(
            "opening_lines_planned",
            accounts=len(to_update),
            open_balance=open_balance,
            commands=len(commands),
        )
        emit(balancing_account, "debit", max(-open_balance, 0), True)
        emit(balancing_account, "credit", -max(open_balance, 0), True)
        _debug.pipeline(
            "opening_balancing_planned",
            balancing_account=balancing_account,
            open_balance=open_balance,
            commands=len(commands),
        )
        return commands

    @_debug.perf.timed
    def _update_opening_move(self, to_update):
        self.check_singleton()

        opening_move = self.account_config_id.account_opening_move_id
        if opening_move and opening_move.state != "draft":
            raise UserError(
                _(
                    'You cannot import the "opening_balance" if the opening move (%s) is already posted. '
                    "If you are absolutely sure you want to modify the opening balance of your accounts, "
                    "reset the move to draft.",
                    self.account_config_id.account_opening_move_id.name,
                )
            )

        AccountMoveLine = self.env["account.move.line"]
        existing_lines = opening_move.line_ids.grouped(
            lambda line: (
                line.account_id,
                "debit"
                if line.balance > 0.0 or line.amount_currency > 0.0
                else "credit",
            )
        )

        balancing_account = self.get_unaffected_earnings_account()
        initial_balance = sum(
            existing_lines.get((balancing_account, "credit"), AccountMoveLine).mapped(
                "credit"
            )
        ) - sum(
            existing_lines.get((balancing_account, "debit"), AccountMoveLine).mapped(
                "debit"
            )
        )

        _debug.pipeline(
            "opening_move_state",
            company=self,
            move=opening_move,
            existing_groups=len(existing_lines),
            balancing_account=balancing_account,
            initial_balance=initial_balance,
            to_update=len(to_update),
        )
        move_values = {}
        if opening_move:
            conversion_date = opening_move.date
        else:
            move_values.update(self._prepare_default_opening_move_values())
            conversion_date = move_values["date"]

        company_currency = self.currency_id
        commands = self._plan_opening_move_lines(
            to_update=to_update,
            balancing_account=balancing_account,
            existing_lines=existing_lines,
            initial_balance=initial_balance,
            is_zero=company_currency.is_zero,
            amount_currency_of=lambda account, balance: company_currency._convert(
                balance, account.currency_id or company_currency, date=conversion_date
            ),
            currency_id_of=lambda account: (account.currency_id or company_currency).id,
            opening_name=_("Opening balance"),
            balancing_name=_("Automatic Balancing Line"),
        )

        _debug.logic(
            "opening_move_decided",
            company=self,
            move=opening_move,
            commands=len(commands),
            action="noop" if not commands else ("write" if opening_move else "create"),
        )
        if not commands:
            return

        move_values["line_ids"] = commands
        if opening_move:
            opening_move.write(move_values)
        else:
            self.account_config_id.account_opening_move_id = self.env[
                "account.move"
            ].create(move_values)

    @_debug.perf.timed
    def action_save_onboarding_company_data(self):
        _debug.lifecycle("action_save_onboarding_company_data", records=self)
        self.check_singleton()
        if self.street:
            ref = "account.onboarding_onboarding_step_company_data"
            self.env["onboarding.onboarding.step"].with_company(
                self
            ).action_validate_step(ref)
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def install_l10n_modules(self):
        if self.env.context.get("chart_template_load"):
            return False
        if res := super().install_l10n_modules():
            env = self.env
            env.flush_all()
            env.transaction.reset()
            for company in self.filtered(
                lambda c: c.country_id and not c.account_config_id.chart_template
            ):
                template_code = (
                    company.parent_id.account_config_id.chart_template
                    or self.env["account.chart.template"]._guess_chart_template(
                        company.country_id
                    )
                )
                _debug.logic(
                    "install_l10n_modules_guessed_template_country",
                    company=company,
                    template_code=template_code,
                    code=company.country_id.code,
                )
                if template_code != "generic_coa":

                    @self.env.cr.precommit.add
                    def try_loading(template_code=template_code, company=company):
                        env["account.chart.template"].try_loading(
                            template_code,
                            env["res.company"].browse(company.id),
                        )

        return res

    def _existing_accounting(self) -> bool:
        self.check_singleton()
        return bool(
            self.env["account.move.line"]
            .sudo()
            .search_count([("company_id", "child_of", self.id)], limit=1)
        )

    def _selection_chart_templates(self):
        return self.env["account.chart.template"]._select_chart_template(
            self.country_id
        )

    @api.model
    @_debug.perf.timed
    def _action_check_hash_integrity(self):
        _debug.lifecycle("_action_check_hash_integrity", records=self)
        return self.env.ref(
            "account.action_report_account_hash_integrity"
        ).report_action(self.id)

    @_debug.perf.timed
    def _check_hash_integrity(self):
        if not self.env.user.has_group("account.group_account_user"):
            raise UserError(
                _("Please contact your accountant to print the Hash integrity result.")
            )

        journals = self.env["account.journal"].search(
            self.env["account.journal"]._check_company_domain(self)
        )
        results = []
        for journal in journals:
            results.extend(self._check_journal_hash_integrity(journal))
        return {
            "results": results,
            "printing_date": format_date(self.env, fields.Date.context_today(self)),
        }

    @_debug.perf.timed
    def _check_journal_hash_integrity(self, journal):
        restricted_flag = "V" if journal.restrict_mode_hash_table else "X"
        query = (
            self.env["account.move"]
            .sudo()
            ._search(
                domain=[
                    ("journal_id", "=", journal.id),
                    ("inalterable_hash", "!=", False),
                ],
                order="secure_sequence_number ASC NULLS LAST, sequence_prefix, sequence_number ASC",
            )
        )
        prefix2result = defaultdict(
            lambda: {
                "first_move": self.env["account.move"],
                "last_move": self.env["account.move"],
                "corrupted_move": self.env["account.move"],
            }
        )
        last_move = self.env["account.move"]
        any_hashed_move = False
        hashed_rows = 0  # debuglog
        hashed_batches = 0  # debuglog
        self.env.execute_query(
            SQL("DECLARE hashed_moves CURSOR FOR %s", query.select())
        )
        try:
            while move_ids := self.env.execute_query(
                SQL("FETCH %s FROM hashed_moves", SQL(str(INTEGRITY_HASH_BATCH_SIZE)))
            ):
                hashed_rows += len(move_ids)  # debuglog
                hashed_batches += 1  # debuglog
                self.env.invalidate_all()
                moves = self.env["account.move"].browse(
                    move_id[0] for move_id in move_ids
                )
                any_hashed_move = True

                hash_version = 1
                for move in moves:
                    prefix_result = prefix2result[move.sequence_prefix]
                    if prefix_result["corrupted_move"]:
                        continue
                    previous_move = (
                        prefix_result["last_move"]
                        if not move.secure_sequence_number
                        else last_move
                    )
                    computed_hash, hash_version = self._recompute_move_hash(
                        move, previous_move.inalterable_hash or "", hash_version
                    )
                    if move.inalterable_hash != computed_hash:
                        _debug.logic(
                            "hash_integrity_corrupted_prefix_version",
                            journal=journal,
                            move=move,
                            sequence_prefix=move.sequence_prefix,
                            hash_version=hash_version,
                        )
                        prefix_result["corrupted_move"] = move
                        continue
                    if not prefix_result["first_move"]:
                        prefix_result["first_move"] = move
                    prefix_result["last_move"] = move
                    last_move = move
        finally:
            self.env.execute_query(SQL("CLOSE hashed_moves"))
        _debug.perf.count(
            "hashed_moves_fetched",
            journal=journal,
            rows=hashed_rows,
            batches=hashed_batches,
        )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "hash_integrity",
                journal=journal,
                hashed=any_hashed_move,
                prefixes={
                    p: (r["first_move"].id, r["last_move"].id, r["corrupted_move"].id)
                    for p, r in prefix2result.items()
                },
            )
        if not any_hashed_move:
            return [self._hash_integrity_no_data_result(journal, restricted_flag)]
        return [
            self._hash_integrity_prefix_result(
                journal, restricted_flag, prefix, prefix_result
            )
            for prefix, prefix_result in prefix2result.items()
        ]

    @staticmethod
    def _recompute_move_hash(move, previous_hash, start_version):
        version = start_version
        computed_hash = move.with_context(hash_version=version)._get_hashes(
            previous_hash
        )[move]
        while move.inalterable_hash != computed_hash and version < MAX_HASH_VERSION:
            version += 1
            computed_hash = move.with_context(hash_version=version)._get_hashes(
                previous_hash
            )[move]
        return computed_hash, version

    def _hash_integrity_no_data_result(self, journal, restricted_flag):
        return {
            "journal_name": journal.name,
            "restricted_by_hash_table": restricted_flag,
            "status": "no_data",
            "msg_cover": _(
                "There is no journal entry flagged for accounting data inalterability yet."
            ),
        }

    def _hash_integrity_prefix_result(
        self, journal, restricted_flag, prefix, prefix_result
    ):
        journal_name = f"{journal.name} ({prefix}...)"
        if corrupted_move := prefix_result["corrupted_move"]:
            return {
                "restricted_by_hash_table": restricted_flag,
                "journal_name": journal_name,
                "status": "corrupted",
                "msg_cover": _(
                    "Corrupted data on journal entry with id %(id)s (%(name)s).",
                    id=corrupted_move.id,
                    name=corrupted_move.name,
                ),
            }
        first_move = prefix_result["first_move"]
        last_move = prefix_result["last_move"]
        return {
            "restricted_by_hash_table": restricted_flag,
            "journal_name": journal_name,
            "status": "verified",
            "msg_cover": _("Entries are correctly hashed"),
            "first_move_name": first_move.name,
            "first_hash": first_move.inalterable_hash,
            "first_move_date": format_date(self.env, first_move.date),
            "last_move_name": last_move.name,
            "last_hash": last_move.inalterable_hash,
            "last_move_date": format_date(self.env, last_move.date),
        }

    @api.model
    def _with_locked_records(self, records, allow_raising=True):
        try:
            records.lock_for_update()
        except LockError as err:
            if not allow_raising:
                return False
            raise UserError(
                _("Some documents are being sent by another process already.")
            ) from err
        return True

    def compute_fiscalyear_dates(self, current_date):
        self.check_singleton()
        date_from, date_to = date_utils.get_fiscal_year(
            current_date,
            day=self.account_config_id.fiscalyear_last_day,
            month=int(self.account_config_id.fiscalyear_last_month),
        )
        return {"date_from": date_from, "date_to": date_to}

    def _set_category_defaults(self, changed_fields=None):
        IrDefault = self.env["ir.default"].sudo()
        if _debug.logic.enabled:
            _debug.logic(
                "category_defaults_scope",
                companies=self,
                all_fields=changed_fields is None,
                expense="expense_account_id" in (changed_fields or ()),
                income="income_account_id" in (changed_fields or ()),
            )
        for company in self:
            if changed_fields is None or "expense_account_id" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_account_expense_categ_id",
                    company.account_config_id.expense_account_id.id,
                    company_id=company.id,
                )
            if changed_fields is None or "income_account_id" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_account_income_categ_id",
                    company.account_config_id.income_account_id.id,
                    company_id=company.id,
                )

    def _check_tax_return_configuration(self):
        return
