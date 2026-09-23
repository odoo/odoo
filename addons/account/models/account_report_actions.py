import base64
import datetime
import re

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.tools import SQL

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES
from odoo.addons.account.tools.report_engines import (
    ACCOUNT_CODES_ENGINE_SPLIT_REGEX,
    ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX,
    ACCOUNT_CODES_ENGINE_TERM_REGEX,
    UNDISTR_LINE_NAME,
)
from odoo.addons.web.controllers.utils import clean_action

_debug = DebugLog(__name__)


class AccountReportActions(models.Model):
    _inherit = "report.formula"

    def _caret_options_initializer_default(self):
        return {
            **super()._caret_options_initializer_default(),
            "account.account": [
                {
                    "name": self.env._("General Ledger"),
                    "action": "caret_option_open_general_ledger",
                },
            ],
            "account.move": [
                {
                    "name": self.env._("View Journal Entry"),
                    "action": "caret_option_open_record_form",
                },
            ],
            "account.move.line": [
                {
                    "name": self.env._("View Journal Entry"),
                    "action": "caret_option_open_record_form",
                    "action_param": "move_id",
                },
            ],
            "account.payment": [
                {
                    "name": self.env._("View Payment"),
                    "action": "caret_option_open_record_form",
                    "action_param": "payment_id",
                },
            ],
            "account.bank.statement": [
                {
                    "name": self.env._("View Bank Statement"),
                    "action": "caret_option_open_statement_line_reco_widget",
                },
            ],
        }

    def _get_caret_option_view_map(self):
        return {
            **super()._get_caret_option_view_map(),
            "account.payment": "account.view_account_payment_form",
            "account.move": "account.view_move_form",
        }

    def _get_default_audit_action_dict(self):
        if not self._reads_ledger():
            return super()._get_default_audit_action_dict()
        return {
            "name": self.env._("Journal Items"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list",
            "views": [(False, "list")],
            "context": {
                "active_test": False,
            },
        }

    def _modify_manual_value(
        self,
        line_id,
        target_column_group_options,
        new_value_str,
        target_expression_id,
        rounding,
    ):
        if not target_column_group_options.get("compute_budget"):
            return super()._modify_manual_value(
                line_id,
                target_column_group_options,
                new_value_str,
                target_expression_id,
                rounding,
            )
        self._action_modify_manual_budget_value(
            line_id,
            target_column_group_options,
            new_value_str,
            target_expression_id,
            rounding,
        )
        return self.env["report.formula.expression"].browse(
            target_expression_id
        ) + self.line_ids.expression_ids.filtered(lambda x: x.engine == "aggregation")

    def _get_reports_parent_menu_id(self):
        return self.env["ir.model.data"]._xmlid_to_res_id(
            "account.menu_finance_reports"
        )

    def _get_domain_audit_line(self, column_group_options, expression, params):
        domain = super()._get_domain_audit_line(
            column_group_options, expression, params
        )
        if column_group_options.get("analytic_accounts"):
            domain &= Domain(
                "analytic_distribution", "in", column_group_options["analytic_accounts"]
            )
        return domain

    @_debug.perf.timed
    def open_account_report_file_download_error_wizard(self, errors, content):
        _debug.lifecycle("open_account_report_file_download_error_wizard", records=self)
        self.check_singleton()

        model = "account.report.file.download.error.wizard"
        vals = {"actionable_errors": errors}

        if content:
            vals["file_name"] = content["file_name"]
            vals["file_content"] = base64.b64encode(
                re.sub(r"\n\s*\n", "\n", content["file_content"]).encode()
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": model,
            "res_id": self.env[model].create(vals).id,
            "target": "new",
            "views": [(False, "form")],
        }

    @_debug.perf.timed
    def caret_option_open_general_ledger(self, options, params):
        # When coming from a specific account, the unfold must only be retained
        # on the specified account. Better performance and more ergonomic
        # as it opens what client asked. And "Unfold All" is 1 clic away.
        options["unfold_all"] = True
        general_ledger = self.env.ref("account.general_ledger_report")
        account_id_to_search = self._get_res_id_from_line_id(
            params["line_id"], "account.account"
        )
        company_id_to_search = self._get_res_id_from_line_id(
            params["line_id"], "res.company"
        )
        if not account_id_to_search and not company_id_to_search:
            raise UserError(
                self.env._(
                    "'Open General Ledger' caret option is only available form report lines targetting "
                    "accounts or Result Brought Forward."
                )
            )

        if account_id_to_search:
            search_content = (
                self.env["account.account"].browse(account_id_to_search).code
            )
        elif len(self.env.companies) == 1:
            search_content = str(UNDISTR_LINE_NAME)
        else:
            search_content = self.env._(
                "%(line_name)s - %(company_name)s",
                line_name=UNDISTR_LINE_NAME,
                company_name=self.env["res.company"].browse(company_id_to_search).name,
            )
        _debug.logic(
            "gl_search_resolved",
            report=self,
            account_id=account_id_to_search,
            company_id=company_id_to_search,
            search_content=search_content,
        )
        gl_options = general_ledger.get_options(options)
        gl_options["not_reset_journals_filter"] = (
            True  # prevents resetting the default journal group
        )
        gl_options["unfold_all"] = True
        gl_options["filter_search_bar"] = search_content

        action_vals = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_account_report_general_ledger"
        )
        action_vals["params"] = {
            "options": gl_options,
            "ignore_session": True,
        }
        action_vals["context"] = dict(
            self.env["ir.actions.actions"]._eval_action_context(action_vals["context"]),
            default_filter_accounts=search_content,
        )

        return action_vals

    def caret_option_open_statement_line_reco_widget(self, options, params):
        model, record_id = self._get_model_info_from_id(params["line_id"])
        record = self.env[model].browse(record_id)
        if record._name == "account.bank.statement.line":
            return record.action_view_recon_st_line()
        elif record._name == "account.bank.statement":
            return record.action_view_bank_reconcile_widget()
        raise UserError(
            self.env._(
                "'View Bank Statement' caret option is only available for report lines targeting bank statements."
            )
        )

    @_debug.perf.timed
    def open_journal_items(self, options, params):
        """Open the journal items view with the proper filters and groups"""
        _debug.lifecycle("open_journal_items", records=self)
        record_model, record_id = self._get_model_info_from_id(params.get("line_id"))
        view_id = (
            self.env.ref(params["view_ref"]).id if params.get("view_ref") else None
        )

        _debug.logic(
            "journal_items_target",
            report=self,
            record_model=record_model,
            record_id=record_id,
            view_ref=params.get("view_ref"),
            journal_type=params.get("journal_type"),
        )
        ctx = {
            "search_default_group_by_account": 1,
            "search_default_posted": 0 if options.get("all_entries") else 1,
            "date_from": options.get("date").get("date_from"),
            "date_to": options.get("date").get("date_to"),
            "search_default_journal_id": params.get("journal_id", False),
            "expand": 1,
        }

        if options["date"].get("date_from"):
            ctx["search_default_date_between"] = 1
        else:
            ctx["search_default_date_before"] = 1

        if options.get("selected_journal_groups"):
            ctx.update(
                {
                    "search_default_journal_group_id": [
                        options["selected_journal_groups"]["id"]
                    ],
                }
            )

        journal_type = params.get("journal_type")
        if journal_type or (
            options.get("selected_journal_groups")
            and options["selected_journal_groups"]["journal_types"]
        ):
            type_to_view_param = {
                "bank": {
                    "filter": "search_default_bank",
                    "view_id": self.env.ref(
                        "account.view_account_move_line_list_grouped_bank_cash"
                    ).id,
                },
                "cash": {
                    "filter": "search_default_cash",
                    "view_id": self.env.ref(
                        "account.view_account_move_line_list_grouped_bank_cash"
                    ).id,
                },
                "general": {
                    "filter": "search_default_misc_filter",
                    "view_id": self.env.ref(
                        "account.view_account_move_line_list_grouped_misc"
                    ).id,
                },
                "sale": {
                    "filter": "search_default_sales",
                    "view_id": self.env.ref(
                        "account.view_account_move_line_list_grouped_sales_purchases"
                    ).id,
                },
                "purchase": {
                    "filter": "search_default_purchases",
                    "view_id": self.env.ref(
                        "account.view_account_move_line_list_grouped_sales_purchases"
                    ).id,
                },
                "credit": {
                    "filter": "search_default_credit",
                    "view_id": self.env.ref("account.view_account_move_line_list").id,
                },
            }
            if options.get("selected_journal_groups"):
                ctx_to_update = {}
                for journal_type in options["selected_journal_groups"]["journal_types"]:
                    ctx_to_update[type_to_view_param[journal_type]["filter"]] = 1
                ctx.update(ctx_to_update)
            else:
                ctx.update(
                    {
                        type_to_view_param[journal_type]["filter"]: 1,
                    }
                )
            view_id = type_to_view_param[journal_type]["view_id"]
            _debug.logic(
                "journal_type_view_chosen",
                report=self,
                journal_type=journal_type,
                from_journal_groups=bool(options.get("selected_journal_groups")),
                view_id=view_id,
            )

        action_domain = [("display_type", "not in", NON_ACCOUNTABLE_DISPLAY_TYPES)]

        if record_model == "account.group":
            if record_id:
                # NB: the root company id is passed as an *unquoted* text param,
                # exactly like the sibling branch below. Under psycopg3 a '%(name)s'
                # inside a SQL string literal is not substituted, so the previous
                # code_store->>'%(root_company_id)s' silently read the literal jsonb
                # key '%s' and matched no account (clicking a group showed nothing).
                query = SQL(
                    """
                    SELECT a.id
                      FROM account_account a
                      JOIN account_group ag
                           ON ag.code_prefix_start <= LEFT(a.code_store->>%(root_company_id)s, char_length(ag.code_prefix_start))
                              AND ag.code_prefix_end >= LEFT(a.code_store->>%(root_company_id)s, char_length(ag.code_prefix_end))
                              AND ag.company_id = %(root_company_id)s
                     WHERE ag.id = %(record_id)s
                           AND a.code_store ? %(root_company_id)s
                """,
                    root_company_id=str(self.env.company.root_id.id),
                    record_id=record_id,
                )
            else:
                query = SQL(
                    """
                    WITH relevant_accounts AS (
                        SELECT id, code_store->>%(root_company_id)s AS code
                          FROM account_account
                         WHERE code_store ? %(root_company_id)s
                    )
                  SELECT a.id
                    FROM relevant_accounts a
                   WHERE NOT EXISTS (
                        SELECT 1
                          FROM account_group ag
                         WHERE ag.company_id = %(root_company_id)s
                               AND LEFT(a.code, char_length(ag.code_prefix_start)) >= ag.code_prefix_start
                               AND LEFT(a.code, char_length(ag.code_prefix_end))   <= ag.code_prefix_end
                    )
                """,
                    root_company_id=str(self.env.company.root_id.id),
                )

            self.env.cr.execute(query)
            account_ids = [account[0] for account in self.env.cr.fetchall()]
            _debug.logic(
                "group_accounts_resolved",
                report=self,
                group_id=record_id,
                ungrouped=not record_id,
                accounts=len(account_ids),
            )
            action_domain += [("account_id", "in", account_ids)]
        elif record_id is None:
            # Default filters don't support the 'no set' value. For this case, we use a domain on the action instead
            model_fields_map = {
                "account.account": "account_id",
                "res.partner": "partner_id",
                "account.journal": "journal_id",
            }
            model_field = model_fields_map.get(record_model)
            _debug.logic(
                "unset_value_domain",
                report=self,
                record_model=record_model,
                model_field=model_field,
            )
            if model_field:
                action_domain += [(model_field, "=", False)]
        else:
            model_default_filters = {
                "account.account": "search_default_account_id",
                "res.partner": "search_default_partner_id",
                "account.journal": "search_default_journal_id",
                "product.product": "search_default_product_id",
                "product.category": "search_default_product_category_id",
            }
            model_filter = model_default_filters.get(record_model)
            if model_filter:
                ctx.update(
                    {
                        "active_id": record_id,
                        model_filter: [record_id],
                    }
                )

        if options:
            for account_type in options.get("account_type", []):
                ctx.update(
                    {
                        f"search_default_{account_type['id']}": (
                            account_type["selected"] and 1
                        )
                        or 0,
                    }
                )

            if options.get("journals") and not ctx["search_default_journal_id"]:
                selected_journals = [
                    journal["id"]
                    for journal in options["journals"]
                    if journal.get("selected")
                ]
                if len(selected_journals) == 1:
                    ctx["search_default_journal_id"] = selected_journals
                elif len(selected_journals) > 1:
                    ctx["search_default_journal_ids"] = True
                    ctx["journal_ids"] = selected_journals

            if options.get("analytic_accounts"):
                analytic_ids = [int(r) for r in options["analytic_accounts"]]
                ctx.update(
                    {
                        "search_default_analytic_accounts": 1,
                        "analytic_ids": analytic_ids,
                    }
                )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "journal_items_action_built",
                report=self,
                view_id=view_id,
                domain_terms=len(action_domain),
                filters=sorted(
                    k for k, v in ctx.items() if k.startswith("search_default_") and v
                ),
            )
        return {
            "name": self._get_action_name(params, record_model, record_id),
            "view_mode": "list,pivot,graph,kanban",
            "res_model": "account.move.line",
            "views": [(view_id, "list")],
            "type": "ir.actions.act_window",
            "domain": action_domain,
            "context": ctx,
        }

    @_debug.perf.timed
    def open_unallocated_items_journal_items(self, options, params):
        _debug.lifecycle("open_unallocated_items_journal_items", records=self)
        _record_model, record_id = self._get_model_info_from_id(params.get("line_id"))
        fiscal_year = self.env.company.compute_fiscalyear_dates(
            fields.Date.to_date(options.get("date").get("date_from"))
        )
        options_for_audit = {
            **options,
            "date": {
                **options["date"],
                "date_from": fields.Date.to_string(fiscal_year["date_from"]),
                "date_to": fields.Date.to_string(fiscal_year["date_to"]),
            },
        }

        action = self.open_journal_items(options=options_for_audit, params=params)
        action["domain"] += self._get_domain_unallocated_earnings_lines(
            action["context"]["date_from"], record_id
        )
        action.get("context", {}).update({"search_default_date_between": 0})
        return action

    @_debug.perf.timed
    def open_unposted_moves(self, options, params=None):
        """Open the list of draft journal entries that might impact the reporting"""
        _debug.lifecycle("open_unposted_moves", records=self)
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_move_journal_line"
        )
        action = clean_action(action, env=self.env)
        action["domain"] = [
            ("state", "=", "draft"),
            ("date", "<=", options["date"]["date_to"]),
        ]
        # overwrite the context to avoid default filtering on 'misc' journals
        action["context"] = {}
        return action

    @_debug.perf.timed
    def open_deferral_entries(self, options, params):
        _debug.lifecycle("open_deferral_entries", records=self)
        domain = self._get_domain_generated_deferral_entries(options)
        deferral_line_ids = self.env["account.move"].search(domain).line_ids.ids
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Deferred Entries"),
            "res_model": "account.move.line",
            "domain": [("id", "in", deferral_line_ids)],
            "views": [(False, "list"), (False, "form")],
            "context": {
                "search_default_group_by_move": True,
                "expand": True,
            },
        }

    @_debug.perf.timed
    def action_display_inactive_sections(self, options):
        _debug.lifecycle("action_display_inactive_sections", records=self)
        self.check_singleton()

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Enable Sections"),
            "view_mode": "list,form",
            "res_model": "report.formula",
            "domain": [
                ("section_main_report_ids", "in", options["sections_source_id"]),
                ("active", "=", False),
            ],
            "views": [(False, "list"), (False, "form")],
            "context": {
                "list_view_ref": "account.account_report_add_sections_tree",
                "active_test": False,
            },
        }

    @_debug.perf.timed
    def action_view_returns(self, options):

        _debug.lifecycle("action_view_returns", records=self)
        date_to = options["date"]["date_to"]
        date_from = options["date"].get("date_from") or fields.Date.to_string(
            fields.Date.from_string(date_to) - relativedelta(months=3)
        )

        # If no return is found for the period and the return type, retry to generate them
        types_with_records = sum(
            (
                return_type
                for return_type, _return_count in self.env[
                    "account.return"
                ]._read_group(
                    domain=Domain(
                        [
                            ("type_id", "in", self.return_type_ids.ids),
                            ("date_to", ">=", date_from),
                            ("date_to", "<=", date_to),
                            ("company_id", "in", self.env.companies.ids),
                        ]
                    ),
                    groupby=["type_id"],
                    aggregates=["__count"],
                )
            ),
            self.env["account.return.type"],
        )

        types_without_record = self.return_type_ids - types_with_records
        _debug.logic(
            "return_types_checked",
            report=self,
            date_from=date_from,
            date_to=date_to,
            types_with_records=types_with_records,
            types_without_record=types_without_record,
        )
        if types_without_record:
            root_companies = (
                self.env["res.company"]
                .sudo()
                .search(
                    [
                        ("account_config_id.account_opening_date", "!=", False),
                        ("id", "parent_of", self.env.companies.ids),
                    ]
                )
            )
            _debug.logic("returns_resync", report=self, root_companies=root_companies)
            self.env["account.return.type"].with_context(
                only_refresh_conditional_types=True
            )._sync_all_returns(root_companies)

        return self.env["account.return"].action_view_tax_return_view(
            additional_context={
                "filter_report_id": self.id,
                "search_default_filter_report_id": True,
            }
        )

    @_debug.perf.timed
    def _action_modify_manual_budget_value(
        self,
        line_id,
        target_column_group_options,
        new_value_str,
        target_expression_id,
        rounding,
    ):
        _debug.lifecycle("_action_modify_manual_budget_value", records=self)
        target_expression = self.env["report.formula.expression"].browse(
            target_expression_id
        )

        if not new_value_str and target_expression.figure_type != "string":
            new_value_str = "0"

        try:
            value_to_set = float_round(float(new_value_str), precision_digits=rounding)
        except ValueError:
            raise UserError(
                self.env._("%s is not a numeric value", new_value_str)
            ) from None

        model, account_id = self._get_model_info_from_id(line_id)
        if model != "account.account":
            raise UserError(
                self.env._("Budget items can only be edited from account lines.")
            )

        # Depending on the expression's formula, the balance of the account could be multiplied by -1
        # within the report. We need to apply the same multiplier on the budget item we create.
        if (
            target_expression.engine == "domain"
            and target_expression.subformula.startswith("-")
        ):
            value_to_set *= -1
        elif target_expression.engine == "account_codes":
            account = self.env["account.account"].browse(account_id)

            # Search for the sign to apply to this account
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(
                target_expression.formula.replace(" ", "")
            ):
                if not token:
                    continue

                token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                multiplicator = -1 if token_match["sign"] == "-" else 1
                prefix = token_match["prefix"]

                tag_match = ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix)
                if tag_match:
                    if tag_match["ref"]:
                        tag = self.env.ref(tag_match["ref"])
                    else:
                        tag = self.env["account.account.tag"].browse(tag_match["id"])

                    account_matches = tag in account.tag_ids
                else:
                    account_matches = account.code.startswith(prefix)

                if account_matches:
                    value_to_set *= multiplicator
                    break

        _debug.logic(
            "budget_value_signed",
            report=self,
            expression=target_expression,
            engine=target_expression.engine,
            account_id=account_id,
            budget=target_column_group_options["compute_budget"],
            value_to_set=value_to_set,
        )
        self.env["account.report.budget"].browse(
            target_column_group_options["compute_budget"]
        )._create_or_update_budget_items(
            value_to_set,
            account_id,
            rounding,
            target_column_group_options["date"]["date_from"],
            target_column_group_options["date"]["date_to"],
        )

    def _get_domain_generated_deferral_entries(self, options):
        """Get the search domain for the generated deferral entries of the current period.

        :param options: the report's `options` dict containing `date_from`, `date_to` and `deferred_report_type`
        :return: a search domain that can be used to get the deferral entries
        """
        if options.get("deferred_report_type") == "expense":
            account_types = ("expense", "expense_depreciation", "expense_direct_cost")
        else:
            account_types = ("income", "income_other")
        date_to = fields.Date.from_string(options["date"]["date_to"])
        date_to_next_reversal = fields.Date.to_string(
            date_to + datetime.timedelta(days=1)
        )
        return [
            ("company_id", "=", self.env.company.id),
            # We exclude the reversal entries of the previous period that fall on the first day of this period
            ("date", ">", options["date"]["date_from"]),
            # We include the reversal entries of the current period that fall on the first day of the next period
            ("date", "<=", date_to_next_reversal),
            ("deferred_original_move_ids", "!=", False),
            ("line_ids.account_id.account_type", "in", account_types),
            ("state", "!=", "cancel"),
        ]
