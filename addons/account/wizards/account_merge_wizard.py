import json

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountMergeWizard(models.TransientModel):
    _name = "account.merge.wizard"
    _description = "Account merge wizard"

    account_ids = fields.Many2many(comodel_name="account.account")
    is_group_by_name = fields.Boolean(
        string="Group by name?",
        default=False,
        help="Tick this checkbox if you want accounts to be grouped by name for merging.",
    )
    wizard_line_ids = fields.One2many(
        comodel_name="account.merge.wizard.line",
        inverse_name="wizard_id",
        compute="_compute_wizard_line_ids",
        store=True,
        readonly=False,
    )
    disable_merge_button = fields.Boolean(compute="_compute_disable_merge_button")

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields_list)
        if not set(fields_list) & {"account_ids", "wizard_line_ids"} or set(
            res.keys()
        ) & {
            "account_ids",
            "wizard_line_ids",
        }:
            _debug.logic(
                "merge_defaults_skipped", reason="accounts_not_requested_or_set"
            )
            return res

        if self.env.context.get("active_model") != "account.account":
            _debug.logic(
                "merge_defaults_rejected",
                reason="not_accounts",
                active_model=self.env.context.get("active_model"),
            )
            raise UserError(_("This can only be used on accounts."))
        if len(self.env.context.get("active_ids") or []) < 2:
            _debug.logic("merge_defaults_rejected", reason="fewer_than_two_accounts")
            raise UserError(_("You must select at least 2 accounts."))

        res["account_ids"] = [Command.set(self.env.context.get("active_ids"))]
        return res

    def _get_grouping_key(self, account):
        self.check_singleton()
        grouping_fields = [
            "account_type",
            "non_trade",
            "currency_id",
            "reconcile",
            "active",
        ]
        if self.is_group_by_name:
            grouping_fields.append("name")
        return tuple(account[field] for field in grouping_fields)

    @api.depends("is_group_by_name", "account_ids")
    @_debug.perf.timed
    def _compute_wizard_line_ids(self):
        for wizard in self:
            accounts = wizard.account_ids._origin.filtered(
                lambda a: a.account_type not in ("asset_bank", "asset_cash")
            )

            wizard_lines_vals_list = []
            sequence = 0
            for grouping_key, group_accounts in accounts.grouped(
                wizard._get_grouping_key
            ).items():
                grouping_key_str = str(grouping_key)
                wizard_lines_vals_list.append(
                    {
                        "display_type": "line_section",
                        "grouping_key": grouping_key_str,
                        "sequence": (sequence := sequence + 1),
                        "account_id": group_accounts[0].id,
                    }
                )
                wizard_lines_vals_list.extend(
                    {
                        "display_type": "account",
                        "account_id": account.id,
                        "grouping_key": grouping_key_str,
                        "is_selected": True,
                        "sequence": (sequence := sequence + 1),
                    }
                    for account in group_accounts
                )

            _debug.pipeline(
                "merge_groups_built",
                wizard=wizard,
                accounts=len(accounts),
                wizard_lines=len(wizard_lines_vals_list),
                group_by_name=wizard.is_group_by_name,
            )
            wizard.wizard_line_ids = [Command.clear()] + [
                Command.create(vals) for vals in wizard_lines_vals_list
            ]

    @api.depends("wizard_line_ids.is_selected", "wizard_line_ids.info")
    def _compute_disable_merge_button(self):
        for wizard in self:
            wizard_lines_to_merge = wizard.wizard_line_ids.filtered(
                lambda l: l.display_type == "account" and l.is_selected and not l.info
            )
            wizard.disable_merge_button = all(
                len(wizard_line_group) < 2
                for wizard_line_group in wizard_lines_to_merge.grouped(
                    "grouping_key"
                ).values()
            )

    def _get_window_action(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Merge Accounts"),
            "view_id": self.env.ref("account.account_merge_wizard_form").id,
            "context": self.env.context,
            "res_model": "account.merge.wizard",
            "res_id": self.id,
            "target": "new",
            "view_mode": "form",
        }

    @_debug.perf.timed
    def action_merge(self):
        _debug.lifecycle("action_merge", records=self)
        for wizard in self:
            wizard_lines_selected = wizard.wizard_line_ids.filtered(
                lambda l: l.display_type == "account" and l.is_selected and not l.info
            )
            for wizard_lines_group in wizard_lines_selected.grouped(
                "grouping_key"
            ).values():
                if len(wizard_lines_group) > 1:
                    self._action_merge(
                        wizard_lines_group.sorted(
                            "account_has_hashed_entries", reverse=True
                        ).account_id
                    )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "sticky": False,
                "message": _("Accounts successfully merged!"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    @api.model
    @_debug.perf.timed
    def _check_access_rights(self, accounts):
        accounts.check_access("write")
        if forbidden_companies := (
            accounts.sudo().company_ids - self.env.user.company_ids
        ):
            raise UserError(
                _(
                    "You do not have the right to perform this operation as you do not have access to the following companies: %s.",
                    ", ".join(c.name for c in forbidden_companies),
                )
            )

    def _get_merged_account_name(self, accounts):
        account_names = self.env.execute_query(
            SQL(
                """
                 SELECT id, name
                   FROM account_account
                  WHERE id IN %(account_ids)s
            """,
                account_ids=tuple(accounts.ids),
            )
        )
        _debug.perf.count("merged_account_names_fetched", rows=len(account_names))
        account_name_by_id = dict(account_names)
        merged_account_name = {}
        for account_id in accounts.ids[::-1]:
            merged_account_name.update(account_name_by_id[account_id])
        return merged_account_name

    def _replace_merged_accounts(
        self, accounts_to_remove, account_to_merge_into, merged_account_name
    ):
        self.env.cr.execute(
            SQL(
                """
             UPDATE account_account
                SET name = %(account_name_json)s
              WHERE id = %(account_to_merge_into_id)s
            """,
                account_name_json=json.dumps(merged_account_name),
                account_to_merge_into_id=account_to_merge_into.id,
            )
        )
        _debug.perf.count("merged_account_name_written", rows=self.env.cr.rowcount)

        self.env.invalidate_all()
        self.env.cr.execute(
            SQL(
                """
             DELETE FROM account_account
              WHERE id IN %(account_ids_to_delete)s
            """,
                account_ids_to_delete=tuple(accounts_to_remove.ids),
            )
        )
        _debug.perf.count("merged_accounts_deleted", rows=self.env.cr.rowcount)

        self.env.registry.clear_cache()

    @api.model
    @_debug.perf.timed
    def _action_merge(self, accounts):
        _debug.lifecycle("_action_merge", records=self)
        company_ids_to_write = accounts.sudo().company_ids
        code_by_company = self.env.execute_query(
            SQL(
                """
            SELECT jsonb_object_agg(key, value)
              FROM account_account, jsonb_each_text(account_account.code_store)
             WHERE account_account.id IN %(account_ids)s
            """,
                account_ids=tuple(accounts.ids),
                to_flush=accounts._fields["code_store"],
            )
        )[0][0]

        account_to_merge_into = accounts[0]
        accounts_to_remove = accounts[1:]
        _debug.pipeline(
            "merge_accounts",
            accounts_to_remove=accounts_to_remove,
            account_to_merge_into=account_to_merge_into,
            codes=code_by_company,
        )

        self._check_access_rights(accounts)

        wiz = self.env["base.partner.merge.automatic.wizard"].new()
        wiz._update_foreign_keys_generic(
            "account.account", accounts_to_remove, account_to_merge_into
        )

        wiz._update_reference_fields_generic(
            "account.account", accounts_to_remove, account_to_merge_into
        )

        self._replace_merged_accounts(
            accounts_to_remove,
            account_to_merge_into,
            self._get_merged_account_name(accounts),
        )

        self.env.cr.execute(
            SQL(
                """
            UPDATE account_account
               SET code_store = %(code_by_company_json)s
             WHERE id = %(account_to_merge_into_id)s
            """,
                code_by_company_json=json.dumps(code_by_company),
                account_to_merge_into_id=account_to_merge_into.id,
            )
        )
        _debug.perf.count("merged_account_codes_written", rows=self.env.cr.rowcount)

        account_to_merge_into.sudo().company_ids = company_ids_to_write
        self.env.add_to_compute(
            self.env["account.account"]._fields["tag_ids"], account_to_merge_into
        )


class AccountMergeWizardLine(models.TransientModel):
    _name = "account.merge.wizard.line"
    _description = "Account merge wizard line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="account.merge.wizard",
        required=True,
        ondelete="cascade",
    )
    grouping_key = fields.Char()
    sequence = fields.Integer()
    display_type = fields.Selection(
        selection=[
            ("line_section", "Section"),
            ("line_subsection", "Subsection"),
            ("account", "Account"),
        ],
        required=True,
    )
    is_selected = fields.Boolean()
    account_id = fields.Many2one(
        comodel_name="account.account",
        readonly=True,
        ondelete="cascade",
    )
    company_ids = fields.Many2many(
        related="account_id.company_ids",
        string="Companies",
    )
    info = fields.Char(
        compute="_compute_info",
        help="Contains either the section name or error message, depending on the line type.",
    )
    account_has_hashed_entries = fields.Boolean(
        compute="_compute_account_has_hashed_entries"
    )

    @api.depends("account_id")
    @_debug.perf.timed
    def _compute_account_has_hashed_entries(self):
        query = self.env["account.move.line"]._search(
            [
                ("account_id", "in", self.account_id.ids),
                ("move_id.inalterable_hash", "!=", False),
            ],
            bypass_access=True,
        )
        query_result = self.env.execute_query(
            query.select(SQL("DISTINCT account_move_line.account_id"))
        )
        _debug.perf.count("hashed_entry_accounts_fetched", rows=len(query_result))
        accounts_with_hashed_entries_ids = {r[0] for r in query_result}
        wizard_lines_with_hashed_entries = self.filtered(
            lambda l: l.account_id.id in accounts_with_hashed_entries_ids
        )
        wizard_lines_with_hashed_entries.account_has_hashed_entries = True
        (self - wizard_lines_with_hashed_entries).account_has_hashed_entries = False

    @api.depends("account_id", "wizard_id.wizard_line_ids.is_selected", "display_type")
    def _compute_info(self):
        for wizard_line in self.filtered(lambda l: l.display_type == "line_section"):
            wizard_line.info = wizard_line._get_group_name()
        for wizard_line_group in (
            self.filtered(lambda l: l.display_type == "account")
            .grouped(lambda l: (l.wizard_id, l.grouping_key))
            .values()
        ):
            wizard_line_group.info = False
            wizard_line_group._update_info_company_conflict()
            wizard_line_group._update_info_hashed_moves_conflict()

    @_debug.perf.timed
    def _get_group_name(self):
        self.check_singleton()

        account_type_label = dict(
            self.pool["account.account"].account_type._description_selection(self.env)
        )[self.account_id.account_type]
        if self.account_id.account_type in ["asset_receivable", "liability_payable"]:
            account_type_label = (
                _("Non-trade %s", account_type_label)
                if self.account_id.non_trade
                else _("Trade %s", account_type_label)
            )

        other_name_elements = []
        if self.account_id.currency_id:
            other_name_elements.append(self.account_id.currency_id.name)

        if self.account_id.reconcile:
            other_name_elements.append(_("Reconcilable"))

        if not self.account_id.active:
            other_name_elements.append(_("Deprecated"))

        if not self.wizard_id.is_group_by_name:
            grouping_key_name = account_type_label
            if other_name_elements:
                grouping_key_name = (
                    f"{grouping_key_name} ({', '.join(other_name_elements)})"
                )
        else:
            grouping_key_name = f"{self.account_id.name} ({', '.join([account_type_label] + other_name_elements)})"

        return grouping_key_name

    def _update_info_company_conflict(self):
        companies_seen = self.env["res.company"]
        account_belonging_to_company = {}
        for wizard_line in self:
            if wizard_line.is_selected and not wizard_line.info:
                if shared_companies := (wizard_line.company_ids & companies_seen):
                    _debug.logic(
                        "merge_company_conflict",
                        wizard_line=wizard_line,
                        companies=shared_companies,
                    )
                    wizard_line.info = _(
                        "Belongs to the same company as %s.",
                        account_belonging_to_company[shared_companies[0]].display_name,
                    )
                else:
                    companies_seen |= wizard_line.company_ids
                    for company in wizard_line.company_ids:
                        if company not in account_belonging_to_company:
                            account_belonging_to_company[company] = (
                                wizard_line.account_id
                            )

    def _update_info_hashed_moves_conflict(self):
        account_to_merge_into = None
        for wizard_line in self:
            if (
                wizard_line.is_selected
                and not wizard_line.info
                and wizard_line.account_has_hashed_entries
            ):
                if not account_to_merge_into:
                    account_to_merge_into = wizard_line.account_id
                else:
                    wizard_line.info = _(
                        "Contains hashed entries, but %s also has hashed entries.",
                        account_to_merge_into.display_name,
                    )
