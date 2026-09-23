from ast import literal_eval
from collections import defaultdict

from odoo import models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.service.model import get_public_method
from odoo.tools import SQL

from odoo.addons.web.controllers.utils import clean_action

_debug = DebugLog(__name__)


class AccountReportActions(models.Model):
    _inherit = "report.formula"

    @_debug.perf.timed
    def action_view_report_form(self, options, params):
        _debug.lifecycle("action_view_report_form", records=self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "report.formula",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
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

    def _caret_options_initializer_default(self):
        return {
            "res.partner": [
                {
                    "name": self.env._("View Partner"),
                    "action": "caret_option_open_record_form",
                },
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
        return {"res.partner": "base.view_partner_form"}

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
    def dispatch_report_action(
        self, options, action, action_param=None, on_sections_source=False
    ):
        """Dispatches calls made by the client to either the report itself, or its custom handler if it exists.
        The action should be a public method, by definition, but a check is made to make sure
        it is not trying to call a private method.
        """
        self.check_singleton()

        if on_sections_source:
            report_to_call = self.env["report.formula"].browse(
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
                    self.env._(
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
                self.env._(
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
        report_line = self.env["report.formula.line"].browse(params["report_line_id"])
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
                query = self.env["report.formula.external.value"]._search(
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
                "name": self.env._("Manual values"),
                "type": "ir.actions.act_window",
                "res_model": "report.formula.external.value",
                "view_mode": "list",
                "views": [(False, "list")],
                "domain": external_values_domain,
            }

        # If we're auditing a groupby line, we need to make sure to restrict the result of what we audit to the right group values
        column = next(
            (
                col
                for col in report_line.report_id.column_ids
                if col.expression_label == expression_label
            ),
            self.env["report.formula.column"],
        )
        if column.custom_audit_action_id:
            action_dict = column.custom_audit_action_id._get_action_dict()
        else:
            action_dict = self._get_default_audit_action_dict()

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

    def _get_default_audit_action_dict(self):
        source_model = self._get_required_source_model()
        return {
            "name": source_model._description,
            "type": "ir.actions.act_window",
            "res_model": source_model._name,
            "view_mode": "list",
            "views": [(False, "list")],
            "context": {
                "active_test": False,
            },
        }

    @_debug.perf.timed
    def action_view_all_variants(self, options, params):
        _debug.lifecycle("action_view_all_variants", records=self)
        return {
            "name": self.env._("All Report Variants"),
            "type": "ir.actions.act_window",
            "res_model": "report.formula",
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
        """Edit a manual value from the report, updating or creating the corresponding report.formula.external.value object.

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

        expressions_to_recompute = self._modify_manual_value(
            line_id,
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

    def _modify_manual_value(
        self,
        line_id,
        target_column_group_options,
        new_value_str,
        target_expression_id,
        rounding,
    ):
        self._action_modify_manual_external_value(
            target_column_group_options,
            new_value_str,
            target_expression_id,
            rounding,
        )
        return self.line_ids.expression_ids.filtered(
            lambda x: x.engine in ("external", "aggregation")
        )

    @_debug.perf.timed
    def action_create_composite_report(self):
        _debug.lifecycle("action_create_composite_report", records=self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "report.formula",
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
            raise UserError(self.env._("This report already has a menuitem."))

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
                "parent_id": self._get_reports_parent_menu_id(),
                "action": f"ir.actions.client,{action.id}",
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def _get_reports_parent_menu_id(self):
        return False

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
                target_report = self.env["report.formula"].browse(
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
                # It can also be a generic report.formula id, as defined by _get_generic_line_id
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
        """Edit a manual value from the report, updating or creating the corresponding report.formula.external.value object.

        :param target_column_group_options: The options dict of the column group where the modification happened.

        :param new_value_str: The new value to be set, as a string.

        :param target_expression_id: The id of the report.formula.expression the manual value belongs to.

        :param rounding: The number of decimal digits to round with.
        """
        _debug.lifecycle("_action_modify_manual_external_value", records=self)
        if len(target_column_group_options["companies"]) > 1:
            raise UserError(
                self.env._(
                    "Editing a manual report line is not allowed when multiple companies are selected."
                )
            )

        # Create the manual value
        target_expression = self.env["report.formula.expression"].browse(
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
            existing_value_to_modify = self.env["report.formula.external.value"].search(
                [
                    *external_values_domain,
                    ("date", "=", date_to),
                ]
            )

            # There should be at most 1
            if len(existing_value_to_modify) > 1:
                raise UserError(
                    self.env._(
                        "Inconsistent data: more than one external value at the same date for a 'most_recent' external line."
                    )
                )
        else:
            existing_external_values = self.env["report.formula.external.value"].search(
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
                raise UserError(self.env._("%s is not a numeric value", new_value_str))
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
            self.env["report.formula.external.value"].create(
                {
                    "name": self.env._("Manual value"),
                    field_name: value_to_set,
                    "date": date_to,
                    "target_report_expression_id": target_expression.id,
                    "company_id": self.env.company.id,
                }
            )

    @_debug.perf.timed
    def _get_domain_audit_line(self, column_group_options, expression, params):
        groupby_domain = Domain(
            self._get_domain_audit_line_groupby(params["calling_line_dict_id"])
        )
        # Aggregate all domains per date scope, then create the final domain.
        audit_or_domains_per_date_scope = defaultdict(list)
        for expression_to_audit in expression._expand_aggregations():
            expression_domain = self._get_domain_expression_audit(
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
        return domain & groupby_domain

    def _get_domain_expression_audit(self, expression_to_audit, options):
        if expression_to_audit.engine == "domain":
            return literal_eval(expression_to_audit.formula)
        return None

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
