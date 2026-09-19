import base64
import datetime
import re
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.service.model import get_public_method
from odoo.tools import SQL

from .account_report_engine import (
    ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX,
    UNDISTR_LINE_NAME,
)
from odoo.addons.account.models.account_report import (
    ACCOUNT_CODES_ENGINE_SPLIT_REGEX,
    ACCOUNT_CODES_ENGINE_TERM_REGEX,
)
from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES
from odoo.addons.web.controllers.utils import clean_action

_debug = DebugLog(__name__)


class AccountReportActions(models.Model):
    _inherit = "account.report"

    @_debug.perf.timed
    def action_view_report_form(self, options, params):
        _debug.lifecycle("action_view_report_form", records=self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.report",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
        }

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

    def _get_caret_options(self):
        return {
            **self._caret_options_initializer_default(),
            **(
                self.env[self.custom_handler_model_name]._caret_options_initializer()
                if self.custom_handler_model_id
                else {}
            ),
        }

    @_debug.perf.timed
    def _caret_options_initializer_default(self):
        return {
            "account.account": [
                {
                    "name": _("General Ledger"),
                    "action": "caret_option_open_general_ledger",
                },
            ],
            "account.move": [
                {
                    "name": _("View Journal Entry"),
                    "action": "caret_option_open_record_form",
                },
            ],
            "account.move.line": [
                {
                    "name": _("View Journal Entry"),
                    "action": "caret_option_open_record_form",
                    "action_param": "move_id",
                },
            ],
            "account.payment": [
                {
                    "name": _("View Payment"),
                    "action": "caret_option_open_record_form",
                    "action_param": "payment_id",
                },
            ],
            "account.bank.statement": [
                {
                    "name": _("View Bank Statement"),
                    "action": "caret_option_open_statement_line_reco_widget",
                },
            ],
            "res.partner": [
                {"name": _("View Partner"), "action": "caret_option_open_record_form"},
            ],
        }

    def caret_option_open_record_form(self, options, params):
        model, record_id = self._get_model_info_from_id(params["line_id"])
        record = self.env[model].browse(record_id)
        target_record = (
            record[params["action_param"]] if "action_param" in params else record
        )

        view_id = self._resolve_caret_option_view(target_record)

        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [
                (view_id, "form")
            ],  # view_id will be False in case the default view is needed
            "res_model": target_record._name,
            "res_id": target_record.id,
            "context": self.env.context,
        }

        if view_id is not None:
            action["view_id"] = view_id

        return action

    def _get_caret_option_view_map(self):
        return {
            "account.payment": "account.view_account_payment_form",
            "res.partner": "base.view_partner_form",
            "account.move": "account.view_move_form",
        }

    def _resolve_caret_option_view(self, target):
        """Retrieve the target view of the caret option.

        :param target:  The target record of the redirection.
        :return: The id of the target view.
        """
        view_map = self._get_caret_option_view_map()

        view_xmlid = view_map.get(target._name)
        if not view_xmlid:
            return None

        return self.env["ir.model.data"]._get_xmlid_target(view_xmlid)[1]

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
                _(
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
            search_content = _(
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
            _(
                "'View Bank Statement' caret option is only available for report lines targeting bank statements."
            )
        )

    @_debug.perf.timed
    def dispatch_report_action(
        self, options, action, action_param=None, on_sections_source=False
    ):
        """Dispatches calls made by the client to either the report itself, or its custom handler if it exists.
        The action should be a public method, by definition, but a check is made to make sure
        it is not trying to call a private method.
        """
        self.check_singleton()

        if on_sections_source:
            report_to_call = self.env["account.report"].browse(
                options["sections_source_id"]
            )
            # on_sections_source and sections_source_id both come from the client,
            # so the link has to be checked here: without it the guard below can
            # never fire on this path, since the recursive call always lands on
            # the very report the options name. Recurse on a copy, too -- the
            # caller still holds the dict we were handed.
            #
            # _init_options_sections sets sections_source_id to self, or to the
            # selected variant; the client sets it to the composite report when a
            # section of one is on screen. Those three are the whole legitimate
            # set, and anything else is a dispatch onto an unrelated report.
            if report_to_call != self and not (
                self in report_to_call.section_report_ids
                or report_to_call in self.variant_report_ids
            ):
                raise UserError(
                    _(
                        "Trying to dispatch an action on a report unrelated to the provided sections source."
                    )
                )
            _debug.logic(
                "dispatch_rerouted_sections_source",
                report=self,
                sections_source=report_to_call,
                action=action,
            )
            return report_to_call.dispatch_report_action(
                {**options, "report_id": report_to_call.id},
                action,
                action_param=action_param,
                on_sections_source=False,
            )

        if self.id not in (options["report_id"], options.get("sections_source_id")):
            raise UserError(
                _(
                    "Trying to dispatch an action on a report not compatible with the provided options."
                )
            )

        model = self
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model and hasattr(self.env[custom_handler_model], action):
            model = self.env[custom_handler_model]
        _debug.logic(
            "dispatch_handler_chosen",
            report=self,
            action=action,
            custom_handler_model=custom_handler_model,
            on_handler=model is not self,
            has_param=action_param is not None,
        )
        report_method = get_public_method(model, action)
        args = [options, action_param] if action_param is not None else [options]
        with _debug.perf(
            "dispatch", cr=self.env.cr, report=self, model=model._name, action=action
        ):
            return report_method(model, *args)

    @_debug.perf.timed
    def action_audit_cell(self, options, params):
        _debug.lifecycle("action_audit_cell", records=self)
        report_line = self.env["account.report.line"].browse(params["report_line_id"])
        expression_label = params["expression_label"]
        expression = report_line.expression_ids.filtered(
            lambda x: x.label == expression_label
        )
        column_group_options = self._get_column_group_options(
            options, params["column_group_key"]
        )

        _debug.logic(
            "audit_target_resolved",
            report=self,
            expression=expression,
            engine=expression.engine,
            column_group_key=params["column_group_key"],
        )
        # Audit of external values
        if expression.engine == "external":
            date_from, date_to = self._get_date_bounds_info(
                column_group_options, expression.date_scope
            )
            external_values_domain = [
                ("target_report_expression_id", "=", expression.id),
                ("date", "<=", date_to),
            ]
            if date_from:
                external_values_domain.append(("date", ">=", date_from))

            if expression.formula == "most_recent":
                query = self.env["account.report.external.value"]._search(
                    external_values_domain, bypass_access=True
                )
                rows = self.env.execute_query(
                    SQL(
                        """
                    SELECT ARRAY_AGG(id)
                    FROM %s
                    WHERE %s
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """,
                        query.from_clause,
                        query.where_clause or SQL("TRUE"),
                    )
                )
                if rows:
                    external_values_domain = [("id", "in", rows[0][0])]
                _debug.logic(
                    "audit_most_recent_narrowed",
                    report=self,
                    expression=expression,
                    narrowed=bool(rows),
                )

            return {
                "name": _("Manual values"),
                "type": "ir.actions.act_window",
                "res_model": "account.report.external.value",
                "view_mode": "list",
                "views": [(False, "list")],
                "domain": external_values_domain,
            }

        # Audit of move lines
        # If we're auditing a groupby line, we need to make sure to restrict the result of what we audit to the right group values
        column = next(
            (
                col
                for col in report_line.report_id.column_ids
                if col.expression_label == expression_label
            ),
            self.env["account.report.column"],
        )
        if column.custom_audit_action_id:
            action_dict = column.custom_audit_action_id._get_action_dict()
        else:
            action_dict = {
                "name": _("Journal Items"),
                "type": "ir.actions.act_window",
                "res_model": "account.move.line",
                "view_mode": "list",
                "views": [(False, "list")],
                "context": {
                    "active_test": False,
                },
            }

        _debug.logic(
            "audit_action_chosen",
            report=self,
            column=column,
            custom_action=column.custom_audit_action_id,
        )
        action = clean_action(action_dict, env=self.env)
        action["domain"] = self._get_domain_audit_line(
            column_group_options, expression, params
        )
        return action

    @_debug.perf.timed
    def action_view_all_variants(self, options, params):
        _debug.lifecycle("action_view_all_variants", records=self)
        return {
            "name": _("All Report Variants"),
            "type": "ir.actions.act_window",
            "res_model": "account.report",
            "view_mode": "list",
            "views": [(False, "list"), (False, "form")],
            "context": {
                "active_test": False,
            },
            "domain": [
                (
                    "id",
                    "in",
                    self._get_variants(options["variants_source_id"])
                    ._is_available_for(options)
                    .ids,
                )
            ],
        }

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
            "name": _("Deferred Entries"),
            "res_model": "account.move.line",
            "domain": [("id", "in", deferral_line_ids)],
            "views": [(False, "list"), (False, "form")],
            "context": {
                "search_default_group_by_move": True,
                "expand": True,
            },
        }

    @_debug.perf.timed
    def action_modify_manual_value(
        self,
        line_id,
        options,
        column_group_key,
        new_value_str,
        target_expression_id,
        rounding,
        json_friendly_column_group_totals,
    ):
        """Edit a manual value from the report, updating or creating the corresponding account.report.external.value object.

        :param options: The option dict the report is evaluated with.

        :param column_group_key: The string identifying the column group into which the change as manual value needs to be done.

        :param new_value_str: The new value to be set, as a string.

        :param rounding: The number of decimal digits to round with.

        :param json_friendly_column_group_totals: The expression totals by column group already computed for this report, in the format returned
                                                  by _get_json_friendly_column_group_totals. These will be used to reevaluate the report, recomputing
                                                  only the expressions depending on the newly-modified manual value, and keeping all the results
                                                  from the previous computations for the other ones.
        """
        _debug.lifecycle("action_modify_manual_value", records=self)
        self.check_singleton()

        target_column_group_options = self._get_column_group_options(
            options, column_group_key
        )
        self._init_currency_table(target_column_group_options)

        if target_column_group_options.get("compute_budget"):
            expressions_to_recompute = self.env["account.report.expression"].browse(
                target_expression_id
            ) + self.line_ids.expression_ids.filtered(
                lambda x: x.engine == "aggregation"
            )
            self._action_modify_manual_budget_value(
                line_id,
                target_column_group_options,
                new_value_str,
                target_expression_id,
                rounding,
            )
        else:
            expressions_to_recompute = self.line_ids.expression_ids.filtered(
                lambda x: x.engine in ("external", "aggregation")
            )
            self._action_modify_manual_external_value(
                target_column_group_options,
                new_value_str,
                target_expression_id,
                rounding,
            )

        _debug.logic(
            "manual_value_target",
            report=self,
            column_group_key=column_group_key,
            budget=target_column_group_options.get("compute_budget"),
            target_expression_id=target_expression_id,
            expressions_to_recompute=expressions_to_recompute,
        )
        # We recompute values for each column group, not only the one we modified a value in; this is important in case some date_scope is used to
        # retrieve the manual value from a previous period.

        all_column_groups_expression_totals = (
            self._convert_json_friendly_column_group_totals(
                json_friendly_column_group_totals,
                expressions_to_exclude=expressions_to_recompute,
            )
        )

        recomputed_expression_totals = self._compute_expression_totals_for_each_column_group(
            expressions_to_recompute,
            options,
            forced_all_column_groups_expression_totals=all_column_groups_expression_totals,
        )
        _debug.pipeline(
            "manual_value_recomputed",
            report=self,
            expressions=len(expressions_to_recompute),
            column_groups=len(recomputed_expression_totals),
        )

        return {
            "lines": self._get_lines(
                options,
                all_column_groups_expression_totals=recomputed_expression_totals,
            ),
            "column_groups_totals": self._get_json_friendly_column_group_totals(
                recomputed_expression_totals
            ),
        }

    @_debug.perf.timed
    def action_display_inactive_sections(self, options):
        _debug.lifecycle("action_display_inactive_sections", records=self)
        self.check_singleton()

        return {
            "type": "ir.actions.act_window",
            "name": _("Enable Sections"),
            "view_mode": "list,form",
            "res_model": "account.report",
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
    def action_create_composite_report(self):
        _debug.lifecycle("action_create_composite_report", records=self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.report",
            "views": [[False, "form"]],
            "context": {
                "default_section_report_ids": self.ids,
            },
        }

    def _get_existing_menuitem(self):
        self.check_singleton()
        action = (
            self.env["ir.actions.client"]
            .search([("name", "=", self.name), ("tag", "=", "account_report")])
            .filtered(
                lambda act: (
                    self.env["ir.actions.actions"]
                    ._eval_action_context(act.context)
                    .get("report_id")
                    == self.id
                )
            )
        )
        menuitem = (
            self.env["ir.ui.menu"]
            .with_context({"active_test": False})
            .search([("action", "=", f"ir.actions.client,{action.id}")])
        )
        return action, menuitem

    @_debug.perf.timed
    def _create_menu_item_for_report(self):
        """Adds a default menu item for this report. This is called by an action on the report, for reports created manually by the user."""
        self.check_singleton()

        action, menuitem = self._get_existing_menuitem()

        if menuitem:
            raise UserError(_("This report already has a menuitem."))

        _debug.logic("menu_action_resolved", report=self, existing_action=action)
        if not action:
            action = self.env["ir.actions.client"].create(
                {
                    "name": self.name,
                    "tag": "account_report",
                    "context": {"report_id": self.id},
                }
            )

        self.env["ir.ui.menu"].create(
            {
                "name": self.name,
                "parent_id": self.env["ir.model.data"]._xmlid_to_res_id(
                    "account.menu_finance_reports"
                ),
                "action": f"ir.actions.client,{action.id}",
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def _get_action_name(self, params, record_model=None, record_id=None):
        if not (record_model or record_id):
            record_model, record_id = self._get_model_info_from_id(
                params.get("line_id")
            )
        return (
            params.get("name")
            or self.env[record_model].browse(record_id).display_name
            or ""
        )

    @_debug.perf.timed
    def execute_action(self, options, params=None):
        action_id = int(params.get("actionId"))
        action = self.env["ir.actions.actions"].sudo().browse([action_id])
        action_type = action.type
        _debug.pipeline(
            "execute_action",
            report=self,
            action_id=action_id,
            action_type=action_type,
            line=params.get("id"),
        )
        action = self.env[action.type].sudo().browse([action_id])
        action_read = clean_action(action.read()[0], env=action.env)

        if action_type == "ir.actions.client":
            # Check if we are opening another report. If so, generate options for it from the current options.
            if action.tag == "account_report":
                target_report = self.env["account.report"].browse(
                    self.env["ir.actions.actions"]._eval_action_context(
                        action_read["context"]
                    )["report_id"]
                )
                new_options = target_report.get_options(previous_options=options)
                action_read.update(
                    {"params": {"options": new_options, "ignore_session": True}}
                )

        if params.get("id"):
            # Add the id of the calling object in the action's context
            if isinstance(params["id"], int):
                # id of the report line might directly be the id of the model we want.
                model_id = params["id"]
            else:
                # It can also be a generic account.report id, as defined by _get_generic_line_id
                model_id = self._get_model_info_from_id(params["id"])[1]

            context = (
                action_read.get("context")
                and self.env["ir.actions.actions"]._eval_action_context(
                    action_read["context"]
                )
            ) or {}
            context.setdefault("active_id", model_id)
            action_read["context"] = context

        return action_read

    @_debug.perf.timed
    def _action_modify_manual_external_value(
        self, target_column_group_options, new_value_str, target_expression_id, rounding
    ):
        """Edit a manual value from the report, updating or creating the corresponding account.report.external.value object.

        :param target_column_group_options: The options dict of the column group where the modification happened.

        :param new_value_str: The new value to be set, as a string.

        :param target_expression_id: The id of the account.report.expression the manual value belongs to.

        :param rounding: The number of decimal digits to round with.
        """
        _debug.lifecycle("_action_modify_manual_external_value", records=self)
        if len(target_column_group_options["companies"]) > 1:
            raise UserError(
                _(
                    "Editing a manual report line is not allowed when multiple companies are selected."
                )
            )

        # Create the manual value
        target_expression = self.env["account.report.expression"].browse(
            target_expression_id
        )
        date_from, date_to = self._get_date_bounds_info(
            target_column_group_options, target_expression.date_scope
        )

        external_values_domain = [
            ("target_report_expression_id", "=", target_expression.id),
            ("company_id", "=", self.env.company.id),
        ]

        if target_expression.formula == "most_recent":
            value_to_adjust = 0
            existing_value_to_modify = self.env["account.report.external.value"].search(
                [
                    *external_values_domain,
                    ("date", "=", date_to),
                ]
            )

            # There should be at most 1
            if len(existing_value_to_modify) > 1:
                raise UserError(
                    _(
                        "Inconsistent data: more than one external value at the same date for a 'most_recent' external line."
                    )
                )
        else:
            existing_external_values = self.env["account.report.external.value"].search(
                [
                    *external_values_domain,
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                ],
                order="date ASC",
            )
            existing_value_to_modify = (
                existing_external_values[-1]
                if existing_external_values
                and str(existing_external_values[-1].date) == date_to
                else None
            )
            value_to_adjust = sum(
                existing_external_values.filtered(
                    lambda x: x != existing_value_to_modify
                ).mapped("value")
            )

        _debug.logic(
            "external_value_located",
            report=self,
            expression=target_expression,
            formula=target_expression.formula,
            date_from=date_from,
            date_to=date_to,
            existing=existing_value_to_modify,
            value_to_adjust=value_to_adjust,
        )
        if not new_value_str and target_expression.figure_type != "string":
            new_value_str = "0"

        try:
            float(new_value_str)
            is_number = True
        except ValueError:
            is_number = False

        if target_expression.figure_type == "string":
            value_to_set = new_value_str
        else:
            if not is_number:
                raise UserError(_("%s is not a numeric value", new_value_str))
            if target_expression.figure_type == "boolean":
                rounding = 0
            value_to_set = float_round(
                float(new_value_str) - value_to_adjust, precision_digits=rounding
            )

        field_name = (
            "value" if target_expression.figure_type != "string" else "text_value"
        )

        _debug.logic(
            "external_value_write_mode",
            report=self,
            expression=target_expression,
            field_name=field_name,
            rounding=rounding,
            update_existing=bool(existing_value_to_modify),
        )
        if existing_value_to_modify:
            existing_value_to_modify[field_name] = value_to_set
            existing_value_to_modify.flush_recordset()
        else:
            self.env["account.report.external.value"].create(
                {
                    "name": _("Manual value"),
                    field_name: value_to_set,
                    "date": date_to,
                    "target_report_expression_id": target_expression.id,
                    "company_id": self.env.company.id,
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
        target_expression = self.env["account.report.expression"].browse(
            target_expression_id
        )

        if not new_value_str and target_expression.figure_type != "string":
            new_value_str = "0"

        try:
            value_to_set = float_round(float(new_value_str), precision_digits=rounding)
        except ValueError:
            raise UserError(_("%s is not a numeric value", new_value_str)) from None

        model, account_id = self._get_model_info_from_id(line_id)
        if model != "account.account":
            raise UserError(_("Budget items can only be edited from account lines."))

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

    @_debug.perf.timed
    def _get_domain_audit_line(self, column_group_options, expression, params):
        groupby_domain = Domain(
            self._get_domain_audit_line_groupby(params["calling_line_dict_id"])
        )
        # Aggregate all domains per date scope, then create the final domain.
        audit_or_domains_per_date_scope = defaultdict(list)
        for expression_to_audit in expression._expand_aggregations():
            expression_domain = self._get_domain_expression_audit_aml(
                expression_to_audit, column_group_options
            )

            if expression_domain is None:
                continue

            date_scope = (
                expression.date_scope
                if expression.subformula
                and expression.subformula.startswith("cross_report")
                else expression_to_audit.date_scope
            )
            audit_or_domains_per_date_scope[date_scope].append(expression_domain)

        if _debug.logic.enabled:
            _debug.logic(
                "audit_domain_scopes",
                report=self,
                expression=expression,
                date_scopes=sorted(audit_or_domains_per_date_scope),
                analytic=bool(column_group_options.get("analytic_accounts")),
            )
        if audit_or_domains_per_date_scope:
            domain = Domain.OR(
                Domain.OR(audit_or_domains)
                & self._get_domain_options(column_group_options, date_scope)
                for date_scope, audit_or_domains in audit_or_domains_per_date_scope.items()
            )
        else:
            # Happens when no expression was provided (empty recordset), or if none of the expressions had a standard engine
            domain = self._get_domain_options(column_group_options, "strict_range")
        domain &= groupby_domain

        # Analytic Filter
        if column_group_options.get("analytic_accounts"):
            domain &= Domain(
                "analytic_distribution", "in", column_group_options["analytic_accounts"]
            )

        return domain

    def _get_domain_audit_line_groupby(self, calling_line_dict_id):
        parsed_line_dict_id = self._parse_line_id(calling_line_dict_id)
        groupby_domain = []
        for markup, _model, grouping_key in parsed_line_dict_id:
            if isinstance(markup, dict) and "groupby" in markup:
                groupby_field_name = markup["groupby"]
                custom_handler_model = self._get_custom_handler_model()
                if custom_handler_model and (
                    custom_groupby_data := self.env[custom_handler_model]
                    ._get_custom_groupby_map()
                    .get(groupby_field_name)
                ):
                    groupby_domain += custom_groupby_data["domain_builder"](
                        grouping_key
                    )
                else:
                    groupby_domain.append((groupby_field_name, "=", grouping_key))

        _debug.logic(
            "audit_groupby_domain",
            report=self,
            segments=len(parsed_line_dict_id),
            conditions=len(groupby_domain),
        )
        return groupby_domain

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
