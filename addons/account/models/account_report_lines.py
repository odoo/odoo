import datetime
import json
import re
from collections import defaultdict
from functools import cmp_to_key

import markupsafe

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_compare, float_is_zero, float_round
from odoo.tools import float_repr, get_lang, html2plaintext
from odoo.tools.formatting import ROUNDING_UNIT_MAPPING
from odoo.tools.misc import format_date, formatLang

from .account_report_engine import (
    LINE_ID_HIERARCHY_DELIMITER,
    NUMBER_FIGURE_TYPES,
)

_debug = DebugLog(__name__)


class AccountReportLines(models.Model):
    _inherit = "account.report"

    @_debug.perf.timed
    def _prepare_columns_from_column_group_vals(
        self, options, all_column_group_vals_in_order
    ):
        def _generate_domain_from_horizontal_group_hash_key_tuple(group_hash_key):
            domain = []
            for field_name, field_value in group_hash_key:
                domain.append((field_name, "=", field_value))
            return domain

        columns = []
        column_groups = {}
        for column_group_val in all_column_group_vals_in_order:
            horizontal_group_key_tuple = self._get_dict_hashable_key_tuple(
                column_group_val["horizontal_groupby_element"]
            )  # Empty tuple if no grouping
            column_group_key = str(
                self._get_dict_hashable_key_tuple(column_group_val)
            )  # Unique identifier for the column group

            column_groups[column_group_key] = {
                "forced_options": column_group_val["forced_options"],
                "forced_domain": _generate_domain_from_horizontal_group_hash_key_tuple(
                    horizontal_group_key_tuple
                ),
            }
            if horizontal_group_key_tuple:
                column_groups[column_group_key]["horizontal_groupby_element"] = (
                    horizontal_group_key_tuple
                )

            # for budget, only one column in needed, regardless of the number of columns in the report
            if any(
                budget_key in column_group_val["forced_options"]
                for budget_key in ("compute_budget", "budget_percentage")
            ):
                columns.append(
                    {
                        "name": "",
                        "column_group_key": column_group_key,
                        "expression_label": "balance",
                        "sortable": False,
                        "figure_type": "monetary",
                        "blank_if_zero": False,
                        "class": "text-nowrap text-end",
                    }
                )

            else:
                columns.extend(
                    {
                        "name": report_column.name,
                        "column_group_key": column_group_key,
                        "expression_label": report_column.expression_label,
                        "sortable": report_column.sortable,
                        "figure_type": report_column.figure_type,
                        "blank_if_zero": report_column.blank_if_zero,
                        "class": f"text-nowrap {('text-end' if report_column.figure_type in NUMBER_FIGURE_TYPES else 'text-center')}",
                    }
                    for report_column in self.column_ids
                )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "columns_prepared",
                report=self,
                column_groups=len(column_groups),
                columns=len(columns),
                horizontal_groups=sum(
                    "horizontal_groupby_element" in group
                    for group in column_groups.values()
                ),
                budget_groups=sum(
                    any(
                        budget_key in group["forced_options"]
                        for budget_key in ("compute_budget", "budget_percentage")
                    )
                    for group in column_groups.values()
                ),
            )
        return columns, column_groups

    @api.model
    def _get_line_from_xml_id(self, lines, xml_id):
        """Helper function to get a specific account report line from the xmlid"""
        report_line = self.env.ref(xml_id, raise_if_not_found=False)
        return next(
            line
            for line in lines
            if self._get_model_info_from_id(line["id"])
            == ("account.report.line", report_line.id)
        )

    @api.model
    @_debug.perf.timed
    def _prepare_line_id(self, current):
        """Build a generic line id string from its list representation, converting
        the None values for model and value to empty strings.
        :param current (list<tuple>): list of tuple(markup, model, value)
        """

        def convert_none(x):
            return x if x is not None and x is not False else ""

        def check_segment(part):
            # The format escapes nothing, so a markup or a non-relational groupby
            # value carrying either delimiter builds an id that cannot be parsed
            # back. Fail here, where the offending value is still in hand, rather
            # than somewhere downstream with an id nobody can trace. The id is not
            # stored anywhere -- it is rebuilt on every render -- but it round-trips
            # to the client and back on fold, expand and audit, and those calls
            # parse it.
            if "~" in part or LINE_ID_HIERARCHY_DELIMITER in part:
                raise UserError(
                    _(
                        "A report line id segment cannot contain %(tilde)s or %(delimiter)s: %(segment)s",
                        tilde="~",
                        delimiter=LINE_ID_HIERARCHY_DELIMITER,
                        segment=part,
                    )
                )
            return part

        return LINE_ID_HIERARCHY_DELIMITER.join(
            "~".join(
                check_segment(str(convert_none(part)))
                for part in (markup, model, value)
            )
            for markup, model, value in current
        )

    @_debug.perf.timed
    def _get_lines(
        self, options, all_column_groups_expression_totals=None, warnings=None
    ):
        self.check_singleton()

        if options["report_id"] != self.id:
            # Should never happen; just there to prevent BIG issues and directly spot them
            raise UserError(
                _(
                    "Inconsistent report_id in options dictionary. Options says %(options_report)s; report is %(report)s.",
                    options_report=options["report_id"],
                    report=self.id,
                )
            )

        # Necessary to ensure consistency of the data if some of them haven't been written in database yet
        self.env.flush_all()

        if warnings is not None:
            self._add_common_warnings(options, warnings)

        # Merge static and dynamic lines in a common list
        if all_column_groups_expression_totals is None:
            self._init_currency_table(options)
            all_column_groups_expression_totals = (
                self._compute_expression_totals_for_each_column_group(
                    self.line_ids.expression_ids,
                    options,
                    warnings=warnings,
                )
            )

        with _debug.perf("dynamic_lines", cr=self.env.cr, report=self):
            dynamic_lines = self._get_dynamic_lines(
                options, all_column_groups_expression_totals, warnings=warnings
            )
        _debug.pipeline(
            "_get_lines",
            report=self,
            line_ids_count=len(self.line_ids),
            dynamic_lines_count=len(dynamic_lines),
        )

        lines = []
        line_cache = {}  # {report_line: report line dict}
        hide_if_zero_lines = self.env["account.report.line"]

        # There are two types of lines:
        # - static lines: the ones generated from self.line_ids
        # - dynamic lines: the ones generated from a call to the functions referred to by self.dynamic_lines_generator
        # This loops combines both types of lines together within the lines list
        for line in self.line_ids:  # _order ensures the sequence of the lines
            # Inject all the dynamic lines whose sequence is inferior to the next static line to add
            while dynamic_lines and line.sequence > dynamic_lines[0][0]:
                lines.append(dynamic_lines.pop(0)[1])

            parent_generic_id = None

            if line.parent_id:
                # Normally, the parent line has necessarily been treated in a previous iteration
                try:
                    parent_generic_id = line_cache[line.parent_id]["id"]
                except KeyError as e:
                    raise UserError(
                        _(
                            "Line '%(child)s' is configured to appear before its parent '%(parent)s'. This is not allowed.",
                            child=line.name,
                            parent=e.args[0].name,
                        )
                    ) from e

            line_dict = self._prepare_static_line_dict(
                options,
                line,
                all_column_groups_expression_totals,
                parent_id=parent_generic_id,
            )
            line_cache[line] = line_dict

            if line.hide_if_zero:
                hide_if_zero_lines += line

            lines.append(line_dict)

        for _dummy, left_dynamic_line in dynamic_lines:
            lines.append(left_dynamic_line)

        # Manage growth comparison
        if options.get("column_percent_comparison") == "growth":
            for line in lines:
                if options["comparison"]["period_order"] == "descending":
                    first_value, second_value = (
                        line["columns"][0]["no_format"],
                        line["columns"][1]["no_format"],
                    )
                else:
                    first_value, second_value = (
                        line["columns"][1]["no_format"],
                        line["columns"][0]["no_format"],
                    )

                green_on_positive = True
                model, line_id = self._get_model_info_from_id(line["id"])

                if model == "account.report.line" and line_id:
                    report_line = self.env["account.report.line"].browse(line_id)
                    compared_expression = report_line.expression_ids.filtered(
                        lambda expr, line=line: (
                            expr.label == line["columns"][0]["expression_label"]
                        )
                    )
                    green_on_positive = compared_expression.green_on_positive

                line["column_percent_comparison_data"] = (
                    self._get_column_percent_comparison_data(
                        options,
                        first_value,
                        second_value,
                        green_on_positive=green_on_positive,
                    )
                )
        # Manage budget comparison
        elif options.get("column_percent_comparison") == "budget":
            for line in lines:
                self._set_budget_column_comparisons(options, line)

        elif options.get("column_percent_comparison") == "analytic_coverage":
            for line in lines:
                first_value, second_value = (
                    line["columns"][0]["no_format"],
                    line["columns"][1]["no_format"],
                )
                line["column_percent_comparison_data"] = (
                    self._get_column_percent_comparison_data(
                        options, first_value, second_value, green_on_positive=False
                    )
                )

        # Manage hide_if_zero lines:
        # - If they have column values: hide them if all those values are 0 (or empty)
        # - If they don't: hide them if all their children's column values are 0 (or empty)
        # Also, hide all the children of a hidden line.
        hidden_lines_dict_ids = set()
        for line in hide_if_zero_lines:
            children_to_check = line
            current = line
            while current:
                children_to_check |= current
                current = current.children_ids

            all_children_zero = True
            hide_candidates = set()
            for child in children_to_check:
                child_line_dict_id = line_cache[child]["id"]

                if child_line_dict_id in hidden_lines_dict_ids:
                    continue
                if all(
                    col.get("is_zero", True) for col in line_cache[child]["columns"]
                ):
                    hide_candidates.add(child_line_dict_id)
                else:
                    all_children_zero = False
                    break

            if all_children_zero:
                hidden_lines_dict_ids |= hide_candidates

        lines[:] = filter(
            lambda x: (
                x["id"] not in hidden_lines_dict_ids
                and x.get("parent_id") not in hidden_lines_dict_ids
            ),
            lines,
        )

        # Create the hierarchy of lines if necessary
        if options.get("hierarchy"):
            lines = self._create_hierarchy(lines, options)

        # Clean up before generating totals, so _add_totals_below_sections doesn't create
        # a total line for a parent whose children were all hidden.
        if hidden_lines_dict_ids:
            lines = self._cleanup_empty_sections(lines)

        # Handle totals below sections for static lines
        lines = self._add_totals_below_sections(lines, options)

        # Unfold lines (static or dynamic) if necessary and add totals below section to dynamic lines
        lines = self._fully_unfold_lines_if_needed(lines, options)

        if self.allow_account_audit_status_on_lines:
            lines = self._add_account_status_on_lines(lines, options)

        self._update_line_names_for_consolidation(lines)

        if self.custom_handler_model_id:
            with _debug.perf(
                "_custom_line_postprocessor",
                cr=self.env.cr,
                report=self,
                custom_handler_model_name=self.custom_handler_model_name,
                lines_count=len(lines),
            ):
                lines = self.env[
                    self.custom_handler_model_name
                ]._custom_line_postprocessor(self, options, lines)

        if warnings is not None:
            custom_handler_name = (
                self.custom_handler_model_name
                or self.root_report_id.custom_handler_model_name
            )
            if custom_handler_name:
                self.env[custom_handler_name]._customize_warnings(
                    self, options, all_column_groups_expression_totals, warnings
                )

        # Format values in columns of lines that will be displayed
        self._format_column_values(options, lines)

        if options.get("export_mode") == "print" and options.get("hide_0_lines"):
            lines = self._filter_out_0_lines(lines)
            lines = self._cleanup_empty_sections(lines)

        if options.get("export_mode") != "file":
            self._postprocess_chatter_for_annotations(lines)

        return lines

    # Deprecated, removed in master.
    @api.model
    def format_column_values(self, options, lines):
        self._format_column_values(options, lines, force_format=True)

        return lines

    def format_column_values_from_client(self, options, lines):
        """Format column values for display. Called via dispatch_report_action when rounding unit changes on client side."""
        self._format_column_values(options, lines, force_format=True)

        return lines

    @_debug.perf.timed
    def _format_column_values(self, options, line_dict_list, force_format=False):
        _debug.logic(
            "column_format_mode",
            report=self,
            lines=len(line_dict_list),
            force_format=force_format,
            raw_file_values=options.get("export_mode") == "file",
            horizontal_group_total=bool(options.get("show_horizontal_group_total")),
        )
        for line_dict in line_dict_list:
            for column_dict in line_dict["columns"]:
                if "name" in column_dict and not force_format:
                    # Columns which have already received a name are assumed to be already formatted; nothing needs to be done for them.
                    # This gives additional flexibility to custom reports, if needed.
                    continue

                if not column_dict:
                    continue
                if column_dict.get("is_zero") and column_dict.get("blank_if_zero"):
                    rslt = ""
                elif options.get("export_mode") == "file":
                    rslt = column_dict.get("no_format", "")
                else:
                    rslt = self.format_value(
                        options,
                        column_dict.get("no_format"),
                        column_dict.get("figure_type"),
                        format_params=column_dict.get("format_params"),
                    )

                column_dict["name"] = rslt

            # Handle the total in case of an horizontal group when there is no comparison and only one level of horizontal group
            if options.get("show_horizontal_group_total"):
                # In case the line has no formula
                if all(column["no_format"] is None for column in line_dict["columns"]):
                    continue
                # In case total below section, some line don't have the value displayed
                if (
                    self.env.company.totals_below_sections
                    and not options.get("ignore_totals_below_sections")
                    and line_dict["unfolded"]
                ):
                    continue

                figure_type_is_valid = all(
                    column["figure_type"] in {"float", "integer", "monetary"}
                    for column in line_dict["columns"]
                )
                total_value = (
                    sum(column["no_format"] for column in line_dict["columns"])
                    if figure_type_is_valid
                    else None
                )
                line_dict["horizontal_group_total_data"] = {
                    "name": self.format_value(
                        options,
                        total_value,
                        line_dict["columns"][0]["figure_type"],
                        format_params=line_dict["columns"][0]["format_params"],
                    ),
                    "no_format": total_value,
                }

    @api.model
    @_debug.perf.timed
    def _prepare_static_line_columns(
        self, line, options, all_column_groups_expression_totals, groupby_model=None
    ):
        line_expressions_map = {expr.label: expr for expr in line.expression_ids}
        # The totals of a line only depend on its column group, not on the individual
        # column, so resolve them once per group rather than once per column.
        reportable_expressions = [
            expr
            for expr in line.expression_ids
            if not expr.label.startswith("_default")
        ]
        line_res_dict_per_col_group = {
            col_group_key: {
                expr.label: all_column_groups_expression_totals[col_group_key][expr]
                for expr in reportable_expressions
            }
            for col_group_key in {
                column_data["column_group_key"] for column_data in options["columns"]
            }
        }
        columns = []
        for column_data in options["columns"]:
            col_group_key = column_data["column_group_key"]
            target_line_res_dict = line_res_dict_per_col_group[col_group_key]

            column_expr_label = column_data["expression_label"]
            column_res_dict = target_line_res_dict.get(column_expr_label, {})
            column_value = column_res_dict.get("value")
            column_has_sublines = column_res_dict.get("sublines_info", False)
            column_expression = line_expressions_map.get(
                column_expr_label, self.env["account.report.expression"]
            )
            figure_type = column_expression.figure_type or column_data["figure_type"]

            # Handle info popup
            info_popup_data = {}

            # Check carryover
            carryover_expr_label = "_carryover_%s" % column_expr_label
            carryover_value = target_line_res_dict.get(carryover_expr_label, {}).get(
                "value", 0
            )
            if self.env.company.currency_id.compare_amounts(0, carryover_value) != 0:
                info_popup_data["carryover"] = self._format_value(
                    options, carryover_value, "monetary"
                )

                carryover_expression = line_expressions_map[carryover_expr_label]
                if carryover_expression.carryover_target:
                    info_popup_data["carryover_target"] = (
                        carryover_expression._get_carryover_target_expression(
                            options
                        ).report_line_name
                    )
                # If it's not set, it means the carryover needs to target the same expression

            applied_carryover_value = target_line_res_dict.get(
                "_applied_carryover_%s" % column_expr_label, {}
            ).get("value", 0)
            if (
                self.env.company.currency_id.compare_amounts(0, applied_carryover_value)
                != 0
            ):
                info_popup_data["applied_carryover"] = self._format_value(
                    options, applied_carryover_value, "monetary"
                )
                info_popup_data["allow_carryover_audit"] = self.env.user.has_group(
                    "base.group_no_one"
                )
                info_popup_data["expression_id"] = line_expressions_map[
                    "_applied_carryover_%s" % column_expr_label
                ]["id"]
                info_popup_data["column_group_key"] = col_group_key

            # Handle manual edition popup
            edit_popup_data = {}
            formatter_params = {}
            if float_rounding_opt := options.get("float_rounding"):
                # This option key allows forcing the rounding of "float' figure type, to include more or less decimals
                formatter_params["digits"] = float_rounding_opt

            if (
                column_expression.engine == "external"
                and column_expression.subformula
                and len(options["companies"]) == 1
            ):
                # Compute rounding for manual values
                rounding = None
                if figure_type == "integer":
                    rounding = 0
                else:
                    rounding_opt_match = re.search(
                        r"\Wrounding\W*=\W*(?P<rounding>\d+)",
                        column_expression.subformula,
                    )
                    if rounding_opt_match:
                        rounding = int(rounding_opt_match.group("rounding"))
                    elif figure_type == "monetary":
                        rounding = self.env.company.currency_id.decimal_places

                if "editable" in column_expression.subformula:
                    edit_popup_data = {
                        "column_group_key": col_group_key,
                        "target_expression_id": column_expression.id,
                        "rounding": rounding,
                        "figure_type": figure_type,
                        "column_value": self.env.company.currency_id.round(column_value)
                        if figure_type == "monetary" and column_value
                        else column_value,
                    }

                formatter_params["digits"] = rounding

            editable_cell_data = self._prepare_editable_cell_data(
                options, col_group_key, groupby_model, column_expression, column_value
            )
            if editable_cell_data:
                edit_popup_data = editable_cell_data

            # Build result
            if (
                column_value is not None
            ):  # In case column value is zero, we still want to go through the condition
                foreign_currency_id = target_line_res_dict.get(
                    f"_currency_{column_expr_label}", {}
                ).get("value")
                if foreign_currency_id:
                    formatter_params["currency"] = self.env["res.currency"].browse(
                        foreign_currency_id
                    )

            column_data = self._prepare_column_dict(
                column_value,
                column_data,
                options=options,
                column_expression=column_expression or None,
                has_sublines=column_has_sublines,
                report_line_id=line.id,
                **formatter_params,
            )

            if info_popup_data:
                column_data["info_popup_data"] = json.dumps(info_popup_data)

            if edit_popup_data:
                column_data["edit_popup_data"] = json.dumps(edit_popup_data)

            columns.append(column_data)

        if _debug.logic.enabled and any(
            "edit_popup_data" in column or "info_popup_data" in column
            for column in columns
        ):
            _debug.logic(
                "line_cells_with_popups",
                line=line,
                columns=len(columns),
                editable=sum("edit_popup_data" in column for column in columns),
                carryover_info=sum("info_popup_data" in column for column in columns),
            )
        return columns

    @_debug.perf.timed
    def _prepare_column_dict(
        self,
        col_value,
        col_data,
        options=None,
        currency=False,
        digits=1,
        column_expression=None,
        has_sublines=False,
        report_line_id=None,
    ):
        # Empty column
        if col_value is None and col_data is None:
            return {}

        col_data = col_data or {}
        column_expression = column_expression or self.env["account.report.expression"]
        options = options or {}

        blank_if_zero = column_expression.blank_if_zero or col_data.get(
            "blank_if_zero", False
        )
        figure_type = column_expression.figure_type or col_data.get(
            "figure_type", "string"
        )

        format_params = {}
        if figure_type == "monetary" and currency:
            format_params["currency_id"] = currency.id
        elif figure_type in ("float", "percentage"):
            format_params["digits"] = digits

        col_group_key = col_data.get("column_group_key")

        return {
            "auditable": col_value is not None
            and column_expression.auditable
            and not options["column_groups"][col_group_key]["forced_options"].get(
                "compute_budget"
            ),
            "blank_if_zero": blank_if_zero,
            "column_group_key": col_group_key,
            "currency": currency,
            "currency_symbol": (currency or self.env.company.currency_id).symbol
            if options.get("multi_currency")
            else None,
            "digits": digits,
            "expression_label": col_data.get("expression_label"),
            "figure_type": figure_type,
            "green_on_positive": column_expression.green_on_positive,
            "has_sublines": has_sublines,
            "is_zero": col_value is None
            or (
                isinstance(col_value, (int, float))
                and figure_type in NUMBER_FIGURE_TYPES
                and self._is_value_zero(
                    col_value, figure_type, format_params, options.get("rounding_unit")
                )
            ),
            "no_format": col_value,
            "format_params": format_params,
            "report_line_id": report_line_id,
            "sortable": col_data.get("sortable", False),
            "comparison_mode": col_data.get("comparison_mode"),
        }

    def _get_column_group_options(self, options, group_key):
        column_group = options["column_groups"][group_key]
        return {
            **options,
            **column_group["forced_options"],
            "forced_domain": options.get("forced_domain", [])
            + column_group["forced_domain"]
            + column_group["forced_options"].get("forced_domain", []),
            "owner_column_group": group_key,
        }

    @api.model
    @api.readonly
    @_debug.perf.timed
    def sort_lines(self, lines, options, result_as_index=False):
        """Sort report lines based on the 'order_column' key inside the options.
        The value of options['order_column'] is a dict with keys 'expression_label' (the column to sort on)
        and 'direction' ('ASC' or 'DESC').
        If this key is missing or falsy, lines is returned directly.

        This method has some limitations:

            - The selected_column must have 'sortable' in its classes.
            - All lines are sorted except:

                - lines having the 'total' class
                - lines with the 'load_more' markup
                - static lines (lines with model 'account.report.line')

            - This only works when each line has an unique id.
            - All lines inside the selected_column must have a 'no_format' value.

        Sorting is hierarchical: sibling children are sorted within their parent, and the
        parents themselves are sorted relative to each other, total lines staying last.

        :param lines:   The report lines.
        :param options: The report options.
        :return:        Lines sorted by the selected column.
        """

        def is_bottom_placement_required(line_elem):
            return self._get_markup(line_elem.get("id")) in ("total", "load_more")

        def _cell_value(line_dict):
            cells = line_dict["columns"]
            if column_index >= len(cells):
                return None
            return cells[column_index].get("no_format")

        def compare_values(a_line, b_line):
            type_seq = {
                type(None): 0,
                bool: 1,
                float: 2,
                int: 2,
                str: 3,
                datetime.date: 4,
                datetime.datetime: 5,
            }

            a_line_dict = lines[a_line] if result_as_index else a_line
            b_line_dict = lines[b_line] if result_as_index else b_line
            a_total = is_bottom_placement_required(a_line_dict)
            b_total = is_bottom_placement_required(b_line_dict)
            a_model = self._get_model_info_from_id(a_line_dict["id"])[0]
            b_model = self._get_model_info_from_id(b_line_dict["id"])[0]

            # static lines are not sorted
            if a_model == b_model == "account.report.line":
                return 0

            if a_total:
                if b_total:  # a_total & b_total
                    return 0
                else:  # a_total & !b_total
                    return -1 if descending else 1
            if b_total:  # => !a_total & b_total
                return 1 if descending else -1

            # A line is free to carry fewer cells than options["columns"] declares --
            # the journal report's tax section headings carry none at all -- so read
            # the cell defensively and let a missing one land in the None bucket
            # below rather than raising IndexError.
            a_val = _cell_value(a_line_dict)
            b_val = _cell_value(b_line_dict)
            # A custom handler is free to put any type in a column; sort what the table
            # does not know about after everything it does, rather than raising.
            type_a = type_seq.get(type(a_val), len(type_seq))
            type_b = type_seq.get(type(b_val), len(type_seq))

            if type_a == type_b:
                return 0 if a_val == b_val else 1 if a_val > b_val else -1
            else:
                return type_a - type_b

        def merge_tree(tree_elem, ls):
            ls.append(tree_elem)

            elem = (
                tree[lines[tree_elem]["id"]]
                if result_as_index
                else tree[tree_elem["id"]]
            )

            for tree_subelem in sorted(elem, key=comp_key, reverse=descending):
                merge_tree(tree_subelem, ls)

        # This is called straight from the client with client-supplied options, so an
        # order_column that names nothing is reachable input. Returning the lines
        # untouched is what the docstring promises; sorting on a column that was never
        # found makes every comparison equal and collapses the tree walk, which drops
        # all but one line.
        order_column = options.get("order_column") or {}
        column_index = next(
            (
                index
                for index, col in enumerate(options["columns"])
                if order_column.get("expression_label") == col["expression_label"]
            ),
            None,
        )
        _debug.logic(
            "sort_column_resolved",
            order_column=order_column,
            column_index=column_index,
            lines=len(lines),
            result_as_index=result_as_index,
        )
        if column_index is None:
            return list(range(len(lines))) if result_as_index else lines

        descending = (
            order_column.get("direction") == "DESC"
        )  # To keep total lines at the end, used in compare_values & merge_tree scopes

        comp_key = cmp_to_key(compare_values)
        sorted_list = []
        tree = defaultdict(list)
        line_ids = {line["id"] for line in lines}

        for index, line in enumerate(lines):
            line_parent = line.get("parent_id") or None

            if result_as_index:
                tree[line_parent].append(index)
            else:
                tree[line_parent].append(line)

        # A line is a root when its parent is not itself in the list: either it has
        # no parent at all, or the parent was not rendered -- the groupby line being
        # unfolded, or the hierarchy's own root, which is referenced but never
        # emitted. Picking the roots by reachability rather than by the None
        # sentinel is what makes "every line comes back" structural; keying on None
        # alone returned an empty list for every multi-root list, silently dropping
        # all of them.
        roots = [
            tree_elem
            for parent, tree_elems in tree.items()
            if parent not in line_ids
            for tree_elem in tree_elems
        ]

        for line in sorted(roots, key=comp_key, reverse=descending):
            merge_tree(line, sorted_list)

        _debug.pipeline(
            "lines_sorted",
            descending=descending,
            roots=len(roots),
            lines=len(lines),
            sorted=len(sorted_list),
        )
        return sorted_list

    @_debug.perf.timed
    def _prepare_column_headers_render_data(self, options):
        column_headers_render_data = {}

        # We only want to consider the columns that are visible in the current report and don't rely on self.column_ids
        # since custom reports could alter them (e.g. for multi-currency purposes)
        columns = [
            col
            for col in options["columns"]
            if col["column_group_key"] == next(k for k in options["column_groups"])
        ]

        # Compute the colspan of each header level, aka the number of single columns it contains at the base of the hierarchy
        level_colspan_list = column_headers_render_data["level_colspan"] = []
        for i in range(len(options["column_headers"])):
            nb_columns = max(len(columns), 1)
            colspan = nb_columns
            budget_col_number = 0

            for level_header in options["column_headers"][i + 1 :]:
                # Separate non-budget and budget headers
                budget_base_count = sum(
                    1
                    for header in level_header
                    if header.get("forced_options", {}).get("budget_base")
                )
                budget_amount_and_percentage_count = sum(
                    any(
                        key in header.get("forced_options", {})
                        for key in ("compute_budget", "budget_percentage")
                    )
                    for header in level_header
                )
                non_budget_count = (
                    len(level_header)
                    - budget_base_count
                    - budget_amount_and_percentage_count
                )

                # budget headers (amount and percentage) can only contain a single column each, regardless of the amount of columns in the report.
                # This implies that we first need to multiply for the 'regular' columns and then add the budget columns.
                colspan *= non_budget_count
                budget_col_number += (
                    budget_base_count * nb_columns
                ) + budget_amount_and_percentage_count

            level_colspan_list.append(colspan + budget_col_number)

        # Compute the number of times each header level will have to be repeated, and its colspan to properly handle horizontal groups/comparisons
        column_headers_render_data["level_repetitions"] = []
        for i in range(len(options["column_headers"])):
            colspan = 1
            for column_header in options["column_headers"][:i]:
                valid_headers_length = sum(
                    1
                    for item in column_header
                    if "no_subheader_division" not in item.get("forced_options", {})
                )
                colspan *= valid_headers_length
            column_headers_render_data["level_repetitions"].append(colspan)

        # Custom reports have the possibility to define custom subheaders that will be displayed between the generic header and the column names.
        column_headers_render_data["custom_subheaders"] = options.get(
            "custom_columns_subheaders", []
        ) * len(options["column_groups"])

        _debug.pipeline(
            "column_headers_render_data",
            report=self,
            header_levels=len(options["column_headers"]),
            columns_per_group=len(columns),
            level_colspan=level_colspan_list,
            level_repetitions=column_headers_render_data["level_repetitions"],
            custom_subheaders=len(column_headers_render_data["custom_subheaders"]),
        )
        return column_headers_render_data

    @_debug.perf.timed
    def _expand_unfoldable_line(
        self,
        expand_function_name,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        horizontal_split_side,
        unfold_all_batch_data=None,
    ):
        if not expand_function_name:
            raise UserError(_("Trying to expand a line without an expansion function."))

        if not progress:
            progress = dict.fromkeys(options["column_groups"], 0)

        expand_function = self._get_custom_report_function(
            expand_function_name, "expand_unfoldable_line"
        )
        with _debug.perf(
            "expand",
            cr=self.env.cr,
            report=self,
            expand_function_name=expand_function_name,
            line=line_dict_id,
            groupby=groupby,
            offset=offset,
        ):
            expansion_result = expand_function(
                line_dict_id,
                groupby,
                options,
                progress,
                offset,
                unfold_all_batch_data=unfold_all_batch_data,
            )

        rslt = expansion_result["lines"]
        _debug.logic(
            "expanded",
            report=self,
            line_dict_id=line_dict_id,
            rslt_count=len(rslt),
            has_more=bool(expansion_result.get("has_more")),
        )

        if horizontal_split_side:
            for line in rslt:
                line["horizontal_split_side"] = horizontal_split_side

        # Apply integer rounding to the result if needed.
        # The groupby expansion function is the only one guaranteed to call the expressions computation,
        # so the values computed for it will already have been rounded if integer rounding is enabled. No need to round them again.
        if expand_function_name != "_report_expand_unfoldable_line_with_groupby":
            self._apply_integer_rounding_to_dynamic_lines(options, rslt)

        if expansion_result.get("has_more"):
            # We only add load_more line for groupby
            next_offset = offset + expansion_result["offset_increment"]
            rslt.append(
                self._get_load_more_line(
                    next_offset,
                    line_dict_id,
                    expand_function_name,
                    groupby,
                    expansion_result.get("progress", 0),
                    options,
                )
            )

        # In some specific cases, we may want to add lines that are always at the end. So they need to be added after the load more line.
        if expansion_result.get("after_load_more_lines"):
            rslt.extend(expansion_result["after_load_more_lines"])

        return self._add_totals_below_sections(rslt, options)

    @_debug.perf.timed
    def _report_expand_unfoldable_line_with_groupby(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        # The line we're expanding might be an inner groupby; we first need to find the report line generating it
        report_line_id = None
        for _markup, model, model_id in reversed(self._parse_line_id(line_dict_id)):
            if model == "account.report.line":
                report_line_id = model_id
                break

        if report_line_id is None:
            raise UserError(
                _(
                    "Trying to expand a group for a line which was not generated by a report line: %s",
                    line_dict_id,
                )
            )

        line = self.env["account.report.line"].browse(report_line_id)

        if "," not in groupby and options["export_mode"] is None:
            # if ',' not in groupby, then its a terminal groupby (like 'id' in 'partner_id, id'), so we can use the 'load more' feature if necessary
            # When printing, we want to ignore the limit.
            limit_to_load = self.load_more_limit or None
        else:
            # Else, we disable it
            limit_to_load = None
            offset = 0

        _debug.logic(
            "groupby_load_limit_decided",
            report=self,
            line=line,
            groupby=groupby,
            limit=limit_to_load,
            offset=offset,
            export_mode=options.get("export_mode"),
        )
        rslt_lines = line._expand_groupby(
            line_dict_id,
            groupby,
            options,
            offset=offset,
            limit=limit_to_load,
            load_one_more=bool(limit_to_load),
            unfold_all_batch_data=unfold_all_batch_data,
        )
        lines_to_load = (
            rslt_lines[: self.load_more_limit] if limit_to_load else rslt_lines
        )

        if not limit_to_load and options["export_mode"] is None:
            lines_to_load = self._regroup_lines_by_name_prefix(
                options,
                rslt_lines,
                "_report_expand_unfoldable_line_groupby_prefix_group",
                line.hierarchy_level,
                groupby=groupby,
                parent_line_dict_id=line_dict_id,
            )

        _debug.pipeline(
            "groupby_lines_ready",
            report=self,
            line=line,
            fetched=len(rslt_lines),
            returned=len(lines_to_load),
            prefix_regroup=not limit_to_load and options["export_mode"] is None,
        )
        return {
            "lines": lines_to_load,
            "offset_increment": len(lines_to_load),
            "has_more": len(lines_to_load) < len(rslt_lines)
            if limit_to_load
            else False,
        }

    @_debug.perf.timed
    def _regroup_lines_by_name_prefix(
        self,
        options,
        lines_to_group,
        expand_function_name,
        parent_level,
        matched_prefix="",
        groupby=None,
        parent_line_dict_id=None,
    ):
        """Postprocesses a list of report line dictionaries in order to regroup them by name prefix and reduce the overall number of lines
        if their number is above a provided threshold (set in the report configuration).

        The lines regrouped under a common prefix will be removed from the returned list of lines; only the prefix line will stay, folded.
        Its expand function must ensure the right sublines are reloaded when unfolding it.

        :param options: Option dict for this report.
        :param lines_to_group: The lines list to regroup by prefix if necessary. They must all have the same parent line (which might be no line at all).
        :param expand_function_name: Name of the expand function to be called on created prefix group lines, when unfolding them
        :param parent_level: Level of the parent line, which generated the lines in lines_to_group. It will be used to compute the level of the prefix group lines.
        :param matched_prefix: A string containing the parent prefix that's already matched. For example, when computing prefix 'ABC', matched_prefix will be 'AB'.
        :param groupby: groupby value of the parent line, which generated the lines in lines_to_group.
        :param parent_line_dict_id: id of the parent line, which generated the lines in lines_to_group.

        :return: lines_to_group, grouped by prefix if it was necessary.
        """
        threshold = options["prefix_groups_threshold"]

        # When grouping by prefix, we ignore the totals
        lines_to_group_without_totals = list(
            filter(lambda x: self._get_markup(x["id"]) != "total", lines_to_group)
        )

        _debug.logic(
            "prefix_grouping_checked",
            report=self,
            parent=parent_line_dict_id,
            matched_prefix=matched_prefix,
            threshold=threshold,
            candidates=len(lines_to_group_without_totals),
            export_mode=options.get("export_mode"),
        )
        if (
            options["export_mode"] == "print"
            or threshold <= 0
            or len(lines_to_group_without_totals) < threshold
        ):
            # No grouping needs to be done
            return lines_to_group

        char_index = len(matched_prefix)
        prefix_groups = defaultdict(list)
        rslt = []
        for line in lines_to_group_without_totals:
            line_name = line["name"].strip()

            if len(line_name) - 1 < char_index:
                rslt.append(line)
            else:
                prefix_groups[line_name[char_index].lower()].append(line)

        float_figure_types = {"monetary", "integer", "float"}
        unfold_all = options["export_mode"] == "print" or options.get("unfold_all")
        for prefix_key, prefix_sublines in sorted(
            prefix_groups.items(), key=lambda x: x[0]
        ):
            # Compute the total of this prefix line, summming all of its content
            prefix_expression_totals_by_group = {}
            for column_index, column_data in enumerate(options["columns"]):
                if column_data["figure_type"] in float_figure_types:
                    # Then we want to sum this column's value in our children
                    for prefix_subline in prefix_sublines:
                        prefix_expr_label_result = (
                            prefix_expression_totals_by_group.setdefault(
                                column_data["column_group_key"], {}
                            )
                        )
                        prefix_expr_label_result.setdefault(
                            column_data["expression_label"], 0
                        )
                        prefix_expr_label_result[column_data["expression_label"]] += (
                            prefix_subline["columns"][column_index].get("no_format")
                            or 0
                        )

            column_values = []
            for column in options["columns"]:
                col_value = prefix_expression_totals_by_group.get(
                    column["column_group_key"], {}
                ).get(column["expression_label"])

                column_values.append(
                    self._prepare_column_dict(col_value, column, options=options)
                )

            line_id = self._get_generic_line_id(
                None,
                None,
                parent_line_id=parent_line_dict_id,
                markup={"groupby_prefix_group": prefix_key},
            )

            sublines_nber = len(prefix_sublines)
            prefix_to_display = prefix_key.upper()

            if re.match(r"\s", prefix_to_display[-1]):
                # In case the last character of the prefix to_display is blank, replace it by "[ ]", to make the space more visible to the user.
                prefix_to_display = f"{prefix_to_display[:-1]}[ ]"

            if sublines_nber == 1:
                prefix_group_line_name = f"{matched_prefix}{prefix_to_display} " + _(
                    "(1 line)"
                )
            else:
                prefix_group_line_name = f"{matched_prefix}{prefix_to_display} " + _(
                    "(%s lines)", sublines_nber
                )

            prefix_group_line = {
                "id": line_id,
                "name": prefix_group_line_name,
                "unfoldable": True,
                "unfolded": unfold_all or line_id in options["unfolded_lines"],
                "columns": column_values,
                "groupby": groupby,
                "level": parent_level + 1,
                "parent_id": parent_line_dict_id,
                "expand_function": expand_function_name,
                "hide_line_buttons": True,
            }
            rslt.append(prefix_group_line)

        _debug.pipeline(
            "prefix_groups_built",
            report=self,
            parent=parent_line_dict_id,
            prefix_groups=len(prefix_groups),
            lines_in=len(lines_to_group_without_totals),
            lines_out=len(rslt),
            unfold_all=bool(unfold_all),
        )
        return rslt

    @_debug.perf.timed
    def _report_expand_unfoldable_line_groupby_prefix_group(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        """Expand function used by prefix_group lines generated for groupby lines."""
        report_line_id = None
        parent_groupby_count = 0
        for markup, model, model_id in reversed(self._parse_line_id(line_dict_id)):
            if model == "account.report.line":
                report_line_id = model_id
                break
            if (
                isinstance(markup, dict) and "groupby" in markup
            ) or "groupby_prefix_group" in markup:
                parent_groupby_count += 1

        if report_line_id is None:
            raise UserError(
                _(
                    "Trying to expand a group for a line which was not generated by a report line: %s",
                    line_dict_id,
                )
            )

        report_line = self.env["account.report.line"].browse(report_line_id)

        matched_prefix = self._get_prefix_groups_matched_prefix_from_line_id(
            line_dict_id
        )
        first_groupby = groupby.split(",")[0]
        expand_options = {
            **options,
            "forced_domain": options.get("forced_domain", [])
            + [
                (
                    f"{f'{first_groupby}.' if first_groupby != 'id' else ''}name",
                    "=ilike",
                    f"{matched_prefix}%",
                )
            ],
        }
        expanded_groupby_lines = report_line._expand_groupby(
            line_dict_id, groupby, expand_options
        )
        parent_level = report_line.hierarchy_level + parent_groupby_count * 2

        lines = self._regroup_lines_by_name_prefix(
            options,
            expanded_groupby_lines,
            "_report_expand_unfoldable_line_groupby_prefix_group",
            parent_level,
            groupby=groupby,
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )

        _debug.pipeline(
            "prefix_group_expanded",
            report=self,
            line=report_line,
            matched_prefix=matched_prefix,
            parent_groupby_count=parent_groupby_count,
            fetched=len(expanded_groupby_lines),
            returned=len(lines),
        )
        return {
            "lines": lines,
            "offset_increment": len(lines),
            "has_more": False,
        }

    def _filter_out_0_lines(self, lines):
        """Returns a list containing all lines that are not zero or that are parent to non-zero lines.
        Can be used to ensure printed report does not include 0 lines, when hide_0_lines is toggled.
        """
        lines_to_hide = set()  # contain line ids to remove from lines
        has_visible_children = set()  # contain parent line ids
        # Traverse lines in reverse to keep track of visible parent lines required by children lines
        for line in reversed(lines):
            is_zero_line = all(
                col.get("figure_type") not in NUMBER_FIGURE_TYPES
                or col.get("is_zero", True)
                for col in line["columns"]
            )
            if is_zero_line and line["id"] not in has_visible_children:
                lines_to_hide.add(line["id"])
            if line.get("parent_id") and line["id"] not in lines_to_hide:
                has_visible_children.add(line["parent_id"])
        _debug.pipeline(
            "zero_lines_filtered",
            report=self,
            lines=len(lines),
            hidden=len(lines_to_hide),
        )
        return list(filter(lambda x: x["id"] not in lines_to_hide, lines))

    def _get_dict_hashable_key_tuple(self, dict_to_convert):
        rslt = []
        for key, value in sorted(dict_to_convert.items()):
            if isinstance(value, dict):
                value = self._get_dict_hashable_key_tuple(value)
            rslt.append((key, value))
        return tuple(rslt)

    @api.model
    def _get_model_info_from_id(self, line_id):
        """Parse the provided generic report line id.

        :param line_id: the report line id (i.e. markup~model~value|markup2~model2~value2 where | is the LINE_ID_HIERARCHY_DELIMITER)
        :return: tuple(model, id) of the report line. Each of those values can be None if the id contains no information about them.
        """
        last_id_tuple = self._parse_line_id(line_id)[-1]
        return last_id_tuple[-2:]

    @api.model
    def _get_markup(self, line_id):
        """Directly returns the markup associated with the provided line_id."""
        return self._parse_line_id(line_id)[-1][0] if line_id else None

    def _get_custom_report_function(self, function_name, prefix):
        """Returns a report function from its name, first checking it to ensure it's private (and raising if it isn't).
        This helper is used by custom report fields containing function names.
        The function will be called on the report's custom handler if it exists, or on the report itself otherwise.
        """
        self.check_singleton()
        function_name_prefix = f"_report_{prefix}_"
        if not function_name.startswith(function_name_prefix):
            _debug.logic(
                "custom_function_bad_prefix",
                report=self,
                function_name=function_name,
            )
            raise UserError(
                _(
                    "Method '%(method_name)s' must start with the '%(prefix)s' prefix.",
                    method_name=function_name,
                    prefix=function_name_prefix,
                )
            )

        if self.custom_handler_model_id:
            handler = self.env[self.custom_handler_model_name]
            if hasattr(handler, function_name):
                _debug.logic(
                    "custom_function_on_handler",
                    report=self,
                    function_name=function_name,
                )
                return getattr(handler, function_name)

        if not hasattr(self, function_name):
            _debug.logic(
                "custom_function_not_found",
                report=self,
                function_name=function_name,
            )
            raise UserError(_("Invalid method “%s”", function_name))
        # function_name was already validated to start with the private prefix above.
        _debug.logic(
            "custom_function_on_report",
            report=self,
            function_name=function_name,
        )
        return getattr(self, function_name)

    @_debug.perf.timed
    def _fully_unfold_lines_if_needed(self, lines, options):
        def line_need_expansion(line_dict):
            return line_dict.get("unfolded") and line_dict.get("expand_function")

        custom_unfold_all_batch_data = None
        lines_in = len(lines)  # debuglog
        expansions = 0  # debuglog

        # If it's possible to batch unfold and we're unfolding all lines, compute the batch, so that individual expansions are more efficient
        if options["unfold_all"] and self.custom_handler_model_id:
            lines_to_expand_by_function = {}
            for line_dict in lines:
                if line_need_expansion(line_dict):
                    lines_to_expand_by_function.setdefault(
                        line_dict["expand_function"], []
                    ).append(line_dict)

            with _debug.perf(
                "_custom_unfold_all_batch_data_generator",
                cr=self.env.cr,
                report=self,
                custom_handler_model_name=self.custom_handler_model_name,
                expand_functions=len(lines_to_expand_by_function),
            ):
                custom_unfold_all_batch_data = self.env[
                    self.custom_handler_model_name
                ]._custom_unfold_all_batch_data_generator(
                    self, options, lines_to_expand_by_function
                )

        _debug.logic(
            "unfold_all_batch_decided",
            report=self,
            unfold_all=bool(options.get("unfold_all")),
            batch_data=custom_unfold_all_batch_data is not None,
            lines=lines_in,
        )
        i = 0
        while i < len(lines):
            # We iterate in such a way that if the lines added by an expansion need expansion, they will get it as well
            line_dict = lines[i]
            if line_need_expansion(line_dict):
                groupby = line_dict.get("groupby")
                progress = line_dict.get("progress")
                to_insert = self._expand_unfoldable_line(
                    line_dict["expand_function"],
                    line_dict["id"],
                    groupby,
                    options,
                    progress,
                    0,
                    line_dict.get("horizontal_split_side"),
                    unfold_all_batch_data=custom_unfold_all_batch_data,
                )
                lines = lines[: i + 1] + to_insert + lines[i + 1 :]
                expansions += 1  # debuglog
            i += 1

        _debug.pipeline(
            "lines_fully_unfolded",
            report=self,
            lines_in=lines_in,
            lines_out=len(lines),
            expansions=expansions,
        )
        return lines

    @_debug.perf.timed
    def _prepare_static_line_dict(
        self, options, line, all_column_groups_expression_totals, parent_id=None
    ):
        line_id = self._get_generic_line_id(
            "account.report.line", line.id, parent_line_id=parent_id
        )
        columns = self._prepare_static_line_columns(
            line, options, all_column_groups_expression_totals
        )
        groupby = line._get_groupby(options)
        has_children = (
            groupby and any(col["has_sublines"] for col in columns)
        ) or bool(line.children_ids)

        rslt = {
            "id": line_id,
            "name": line.name,
            "groupby": groupby,
            "unfoldable": line.foldable and has_children,
            "unfolded": (not line.foldable and (groupby or has_children))
            or line_id in options["unfolded_lines"]
            or (has_children and options["unfold_all"]),
            "columns": columns,
            "level": line.hierarchy_level,
            "page_break": line.print_on_new_page,
            "action_id": line.action_id.id,
            "expand_function": (
                groupby and "_report_expand_unfoldable_line_with_groupby"
            )
            or None,
        }

        if _debug.logic.enabled and groupby:
            _debug.logic(
                "static_line_groupby",
                line=line,
                groupby=groupby,
                has_children=bool(has_children),
                unfoldable=bool(rslt["unfoldable"]),
                unfolded=bool(rslt["unfolded"]),
            )
        if line.horizontal_split_side:
            rslt["horizontal_split_side"] = line.horizontal_split_side

        if parent_id:
            rslt["parent_id"] = parent_id

        if options["export_mode"] == "file":
            rslt["code"] = line.code

        if options["show_debug_column"]:
            first_group_key = next(iter(options["column_groups"].keys()))
            column_group_totals = all_column_groups_expression_totals[first_group_key]
            # Only consider the first column group, as show_debug_column is only true if there is but one.

            engine_selection_labels = dict(
                self.env["account.report.expression"]
                ._fields["engine"]
                ._description_selection(self.env)
            )
            expressions_detail = defaultdict(list)
            col_expression_to_figure_type = {
                column.get("expression_label"): column.get("figure_type")
                for column in options["columns"]
            }
            for expression in line.expression_ids.filtered(
                lambda x: not x.label.startswith("_default")
            ):
                engine_label = engine_selection_labels[expression.engine]
                figure_type = (
                    expression.figure_type
                    or col_expression_to_figure_type.get(expression.label)
                    or "none"
                )
                value = self.format_value(
                    options, column_group_totals[expression]["value"], figure_type
                )
                if not isinstance(value, (str, int, float, bool, type(None))):
                    # figure_type "none" returns the value unformatted, so anything the
                    # engine produced reaches json.dumps as-is. Stringify it here rather
                    # than let the dump fail: by then the offending expression is no
                    # longer identifiable.
                    value = str(value)
                expressions_detail[engine_label].append(
                    (
                        expression.label,
                        {
                            "formula": expression.formula,
                            "subformula": expression.subformula,
                            "value": value,
                        },
                    )
                )

            # Sort results so that they can be rendered nicely in the UI
            for details in expressions_detail.values():
                details.sort(key=lambda x: x[0])
            sorted_expressions_detail = sorted(
                expressions_detail.items(), key=lambda x: x[0]
            )

            if sorted_expressions_detail:
                rslt["debug_popup_data"] = json.dumps(
                    {"expressions_detail": sorted_expressions_detail}
                )
        return rslt

    @_debug.perf.timed
    def _get_dynamic_lines(
        self, options, all_column_groups_expression_totals, warnings=None
    ):
        if self.custom_handler_model_id:
            with _debug.perf(
                "_dynamic_lines_generator",
                cr=self.env.cr,
                report=self,
                custom_handler_model_name=self.custom_handler_model_name,
            ):
                rslt = self.env[
                    self.custom_handler_model_name
                ]._dynamic_lines_generator(
                    self,
                    options,
                    all_column_groups_expression_totals,
                    warnings=warnings,
                )
            self._apply_integer_rounding_to_dynamic_lines(
                options, (line for _sequence, line in rslt)
            )
            return rslt
        return []

    @_debug.perf.timed
    def _apply_integer_rounding_to_dynamic_lines(self, options, dynamic_lines):
        if options.get("integer_rounding_enabled"):
            for line in dynamic_lines:
                for column_dict in line.get("columns", []):
                    if (
                        "name" not in column_dict
                        and column_dict.get("figure_type") == "monetary"
                        and column_dict.get("no_format")
                    ):
                        # If 'name' is already in it, no need to round the amount ; it is forced by the custom report already
                        column_dict["no_format"] = float_round(
                            column_dict["no_format"],
                            precision_digits=0,
                            rounding_method=options["integer_rounding"],
                        )

    @_debug.perf.timed
    def _add_totals_below_sections(self, lines, options):
        """Returns a new list, corresponding to lines with the required total lines added as sublines of the sections it contains."""
        if _debug.logic.enabled:
            _debug.logic(
                "totals_below_sections_checked",
                report=self,
                company_setting=self.env.company.totals_below_sections,
                ignored=bool(options.get("ignore_totals_below_sections")),
                lines=len(lines),
            )
        if not self.env.company.totals_below_sections or options.get(
            "ignore_totals_below_sections"
        ):
            return lines

        # Gather the lines needing the totals
        lines_needing_total_below = set()
        for line_dict in lines:
            line_markup = self._get_markup(line_dict["id"])

            if line_markup != "total":
                # If we are on the first level of an expandable line, we arelady generate its total
                if line_dict.get("unfoldable") or (
                    line_dict.get("unfolded") and line_dict.get("expand_function")
                ):
                    lines_needing_total_below.add(line_dict["id"])

                # All lines that are parent of other lines need to receive a total
                line_parent_id = line_dict.get("parent_id")
                if line_parent_id:
                    lines_needing_total_below.add(line_parent_id)

        # Inject the totals
        if lines_needing_total_below:
            lines_with_totals_below = []
            totals_below_stack = []
            for line_dict in lines:
                while totals_below_stack and not line_dict["id"].startswith(
                    totals_below_stack[-1]["parent_id"] + LINE_ID_HIERARCHY_DELIMITER
                ):
                    lines_with_totals_below.append(totals_below_stack.pop())

                lines_with_totals_below.append(line_dict)

                if line_dict["id"] in lines_needing_total_below and any(
                    col.get("no_format") is not None for col in line_dict["columns"]
                ):
                    totals_below_stack.append(
                        self._generate_total_below_section_line(line_dict)
                    )

            while totals_below_stack:
                lines_with_totals_below.append(totals_below_stack.pop())

            _debug.pipeline(
                "section_totals_added",
                report=self,
                sections=len(lines_needing_total_below),
                totals=len(lines_with_totals_below) - len(lines),
                lines_out=len(lines_with_totals_below),
            )
            return lines_with_totals_below

        return lines

    @_debug.perf.timed
    def _cleanup_empty_sections(self, lines):
        """Resets the fold state for parents left without visible children, and removes their orphaned total lines.
        The total line removal only applies when called after _add_totals_below_sections.
        """
        # Collect parent IDs that still have at least one non-total child visible.
        # Total lines are generated from the parent itself and don't count as expandable children.
        parents_with_non_total_child = set()
        markups = {}
        for line in lines:
            markup = self._get_markup(line["id"])
            markups[line["id"]] = markup
            parent_id = line.get("parent_id")
            if parent_id is not None and markup != "total":
                parents_with_non_total_child.add(parent_id)

        result = []
        folds_reset = 0  # debuglog
        for line in lines:
            # Lines with an expand_function load their children on demand, so hide_if_zero doesn't affect them.
            if line.get("expand_function"):
                result.append(line)
            elif markups[line["id"]] == "total":
                # Keep report-level totals (no parent), and keep section totals only if
                # their parent still has non-total children.
                if (
                    line.get("parent_id") is None
                    or line.get("parent_id") in parents_with_non_total_child
                ):
                    result.append(line)
            elif line["id"] in parents_with_non_total_child:
                result.append(line)
            else:
                line["unfoldable"] = False
                line["unfolded"] = False
                result.append(line)
                folds_reset += 1  # debuglog

        _debug.pipeline(
            "empty_sections_cleaned",
            report=self,
            lines_in=len(lines),
            lines_out=len(result),
            parents_kept=len(parents_with_non_total_child),
            folds_reset=folds_reset,
        )
        return result

    @api.model
    @_debug.perf.timed
    def _get_load_more_line(
        self, offset, parent_line_id, expand_function_name, groupby, progress, options
    ):
        """Returns a 'Load more' line allowing to reach the subsequent elements of an unfolded line with an expand function if the maximum
        limit of sublines is reached (we load them by batch, using the load_more_limit field's value).

        :param offset: The offset to be passed to the expand function to generate the next results, when clicking on this 'load more' line.

        :param parent_line_id: The generic id of the line this load more line is created for.

        :param expand_function_name: The name of the expand function this load_more is created for (so, the one of its parent).

        :param progress: A json-formatted dict(column_group_key, value) containing the progress value for each column group, as it was
                         returned by the expand function. This is for example used by reports such as the general ledger, whose lines display a
                         cumulative sum of their balance and the one of all the previous lines under the same parent. In this case, progress
                         will be the total sum of all the previous lines before the load_more line, that the subsequent lines will need to use as
                         base for their own cumulative sum.

        :param options: The options dict corresponding to this report's state.
        """
        _debug.logic(
            "load_more_line_added",
            report=self,
            parent=parent_line_id,
            expand_function=expand_function_name,
            groupby=groupby,
            offset=offset,
        )
        return {
            "id": self._get_generic_line_id(
                None, None, parent_line_id=parent_line_id, markup="load_more"
            ),
            "name": _("Load more..."),
            "parent_id": parent_line_id,
            "expand_function": expand_function_name,
            "columns": [{} for col in options["columns"]],
            "unfoldable": False,
            "unfolded": False,
            "offset": offset,
            "groupby": groupby,  # We keep the groupby value from the parent, so that it can be propagated through js
            "progress": progress,
        }

    @api.model
    def _get_prefix_groups_matched_prefix_from_line_id(self, line_dict_id):
        matched_prefix = ""
        for markup, _model, _record_id in self._parse_line_id(line_dict_id):
            if markup and isinstance(markup, dict) and "groupby_prefix_group" in markup:
                prefix_piece = markup["groupby_prefix_group"]
                matched_prefix += prefix_piece.upper()
            else:
                # Might happen if a groupby is grouped by prefix, then a subgroupby is grouped by another subprefix.
                # In this case, we want to reset the prefix group to only consider the one used in the subgroupby.
                matched_prefix = ""

        return matched_prefix

    @api.model
    def format_value(self, options, value, figure_type, format_params=None):
        if format_params is None:
            format_params = {}

        return self._format_value(
            options=options,
            value=value,
            figure_type=figure_type,
            format_params=format_params,
        )

    @_debug.perf.timed
    def _format_value(self, options, value, figure_type, format_params=None):
        """Formats a value for display in a report (not especially numerical). figure_type provides the type of formatting we want."""
        if value is None:
            return ""

        if figure_type == "none":
            return value

        if isinstance(value, str) or figure_type == "string":
            return str(value)

        if format_params is None:
            format_params = {}

        formatLang_params = {
            "rounding_method": "HALF-UP",
            "rounding_unit": options.get("rounding_unit") or "decimals",
        }

        if figure_type == "monetary":
            currency = (
                self.env["res.currency"].browse(format_params["currency_id"])
                if "currency_id" in format_params
                else self.env.company.currency_id
            )
            if options.get("multi_currency"):
                formatLang_params["currency_obj"] = currency
            else:
                formatLang_params["digits"] = currency.decimal_places

        elif figure_type == "integer":
            formatLang_params["digits"] = 0

        elif figure_type == "boolean":
            return _("Yes") if bool(value) else _("No")

        elif figure_type in ("date", "datetime"):
            return format_date(self.env, value)

        else:
            formatLang_params["digits"] = format_params.get("digits", 1)

        if self._is_value_zero(
            value, figure_type, format_params, formatLang_params["rounding_unit"]
        ):
            # Make sure -0.0 becomes 0.0
            value = abs(value)

        if self.env.context.get("no_format"):
            return value

        formatted_amount = formatLang(self.env, value, **formatLang_params)

        if figure_type == "percentage":
            return f"{formatted_amount}%"

        return formatted_amount

    @api.model
    @_debug.perf.timed
    def _is_value_zero(
        self, amount, figure_type, format_params, rounding_unit="decimals"
    ):
        """Tell whether a value renders as zero, at the precision it is rendered with.

        The caller must pass the same rounding_unit that reaches _format_value: formatLang
        divides by the unit and drops every decimal, so at any unit other than "decimals"
        a value is displayed as 0 long before the currency would call it zero. Answering
        this from format_params alone makes a report shown in millions render -400,000 as
        "-0", and makes hide_0_lines keep rows whose every cell reads 0.
        """
        if amount is None:
            return True

        if figure_type not in NUMBER_FIGURE_TYPES:
            return False

        if rounding_unit and rounding_unit != "decimals":
            return float_is_zero(
                amount / ROUNDING_UNIT_MAPPING[rounding_unit], precision_digits=0
            )

        if figure_type == "monetary":
            currency = (
                self.env["res.currency"].browse(format_params["currency_id"])
                if "currency_id" in format_params
                else self.env.company.currency_id
            )
            return currency.is_zero(amount)

        return float_is_zero(amount, precision_digits=format_params.get("digits", 1))

    ####################################################
    # LINE IDS MANAGEMENT HELPERS
    ####################################################
    @_debug.perf.timed
    def _get_generic_line_id(self, model_name, value, markup=None, parent_line_id=None):
        """Generates a generic line id from the provided parameters.

        Such a generic id consists of a string repeating 1 to n times the following pattern:
        markup-model-value, each occurence separated by a LINE_ID_HIERARCHY_DELIMITER character from the previous one.

        Each pattern corresponds to a level of hierarchy in the report, so that
        the n-1 patterns starting the id of a line actually form the id of its generator line.
        EX: a~b~c|d~e~f|g~h~i => This line is a subline generated by a~b~c|d~e~f where | is the LINE_ID_HIERARCHY_DELIMITER.

        Each pattern consists of the three following elements:
        - markup:  a (possibly empty) free string or json-formatted dict allowing finer identification of the line
                   (like the name of the field for account.accounting.reports)

        - model:   the model this line has been generated for, or an empty string if there is none

        - value:   the groupby value for this line (typically the id of a record
                   or the value of a field), or an empty string if there isn't any.
        """
        self.check_singleton()

        if parent_line_id:
            parent_id_list = self._parse_line_id(parent_line_id, markup_as_string=True)
        else:
            parent_id_list = [(None, "account.report", self.id)]

        # In case the markup is a dict, it must be converted to a string, but in a way such that the keys are ordered alphabetically.
        # This is useful, notably for annotations where the ids of the lines are stored, therefore requiring a consistent ordering
        if isinstance(markup, dict):
            markup = json.dumps(markup, sort_keys=True)

        return self._prepare_line_id(parent_id_list + [(markup, model_name, value)])

    @api.model
    def _parse_markup(self, markup):
        if not markup:
            return markup
        try:
            result = json.loads(markup)
        except json.JSONDecodeError:  # the markup is not a JSON object
            return markup
        if isinstance(result, dict):
            return result

        return markup

    @api.model
    @_debug.perf.timed
    def _parse_line_id(self, line_id, markup_as_string=False):
        """Parse the provided string line id and convert it to its list representation.
        Empty strings for model and value will be converted to None.

        For instance if line_id is markup1~account.account~5|markup2~res.partner~8 (where | is the LINE_ID_HIERARCHY_DELIMITER),
        it will return [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8)]
        :param line_id (str): the generic line id to parse
        """
        if not line_id:
            return []

        # Line ids reach this from the client on every caret, audit, unfold and
        # sort action, so a malformed one is input, not a programming error: it
        # has to surface as a UserError rather than as a 500.
        def parse_segment(key):
            parts = key.rsplit("~", 2)
            if len(parts) != 3:
                raise UserError(
                    _("Malformed report line id: %(line_id)s", line_id=line_id)
                )
            markup, model, value = parts
            if model and value:
                try:
                    value = int(value)
                except ValueError:
                    raise UserError(
                        _(
                            "Malformed report line id: %(line_id)s. %(value)s is not a valid %(model)s id.",
                            line_id=line_id,
                            value=value,
                            model=model,
                        )
                    ) from None
            else:
                value = value or None
            return (
                # When there is a model, value is an id, so we cast it to an int. Else, we keep the original value (for groupby lines on
                # non-relational fields, for example).
                self._parse_markup(markup) if not markup_as_string else markup,
                model or None,
                value,
            )

        return [
            parse_segment(key) for key in line_id.split(LINE_ID_HIERARCHY_DELIMITER)
        ]

    @_debug.perf.timed
    def _generate_columns_group_vals_recursively(
        self, next_levels_headers, previous_levels_group_vals
    ):
        if next_levels_headers:
            rslt = []

            # Separate headers into those with "no_subheader_division" and those without
            headers_with_no_subdivision = [
                header
                for header in next_levels_headers[0]
                if "no_subheader_division" in header.get("forced_options", {})
            ]
            valid_next_level_headers = [
                header
                for header in next_levels_headers[0]
                if "no_subheader_division" not in header.get("forced_options", {})
            ]

            # Process headers without "no_subheader_division"
            for header_element in valid_next_level_headers:
                current_level_group_vals = {
                    key: {
                        **previous_levels_group_vals.get(key, {}),
                        **header_element.get(key, {}),
                    }
                    for key in previous_levels_group_vals
                }
                rslt += self._generate_columns_group_vals_recursively(
                    next_levels_headers[1:], current_level_group_vals
                )

            # Process headers with "no_subheader_division" as standalone groups
            for header_element in headers_with_no_subdivision:
                current_level_group_vals = {
                    key: {
                        **previous_levels_group_vals.get(key, {}),
                        **header_element.get(key, {}),
                    }
                    for key in previous_levels_group_vals
                }
                rslt.append(current_level_group_vals)

            return rslt
        else:
            return [previous_levels_group_vals]

    @api.model
    @_debug.perf.timed
    def _prepare_parent_line_id(self, current):
        """Build the parent_line id based on the current position in the report.

        For instance, if current is [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8)], it will return
        markup1~account.account~5
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        to_process = [
            (json.dumps(markup) if isinstance(markup, dict) else markup, model, value)
            for markup, model, value in current[:-1]
        ]
        return self._prepare_line_id(to_process)

    @api.model
    def _get_unfolded_lines(self, lines, parent_line_id):
        """Return a list of all children lines for specified parent_line_id.
        NB: It will return the parent_line itself!

        For instance if parent_line_ids is '~account.report.line~84|{"groupby": "currency_id"}~res.currency~174'
        (where | is the LINE_ID_HIERARCHY_DELIMITER), it will return every subline for this currency.
        :param lines: list of report lines
        :param parent_line_id: id of a specified line
        :return: A list of all children lines for a specified parent_line_id
        """
        return [line for line in lines if line["id"].startswith(parent_line_id)]

    @api.model
    def _get_res_id_from_line_id(self, line_id, target_model_name):
        """Parses the provided generic line id and returns the most local (i.e. the furthest on the right) record id it contains which
        corresponds to the provided model name. If line_id does not contain anything related to target_model_name, None will be returned.

        For example, parsing ~account.move~1|~res.partner~2|~account.move~3 (where | is the LINE_ID_HIERARCHY_DELIMITER)
        with target_model_name='account.move' will return 3.
        """
        dict_result = self._get_res_ids_from_line_id(line_id, [target_model_name])
        return dict_result[target_model_name] if dict_result else None

    @api.model
    def _get_res_ids_from_line_id(self, line_id, target_model_names):
        """Parses the provided generic line id and returns the most local (i.e. the furthest on the right) record ids it contains which
        correspond to the provided model names, in the form {model_name: res_id}. If a model is not present in line_id, its model will be absent
        from the resulting dict.

        For example, parsing ~account.move~1|~res.partner~2|~account.move~3 with target_model_names=['account.move', 'res.partner'] will return
        {'account.move': 3, 'res.partner': 2}.
        """
        result = {}
        models_to_find = set(target_model_names)
        for _markup, model, value in reversed(self._parse_line_id(line_id)):
            if model in models_to_find:
                result[model] = value
                models_to_find.remove(model)

        return result

    @_debug.perf.timed
    def _prepare_subline_id(self, parent_line_id, subline_id_postfix):
        """Creates a new subline id by concatanating parent_line_id with the provided id postfix."""
        return f"{parent_line_id}{LINE_ID_HIERARCHY_DELIMITER}{subline_id_postfix}"

    @_debug.perf.timed
    def _generate_total_below_section_line(self, section_line_dict):
        return {
            **section_line_dict,
            "id": self._get_generic_line_id(
                None, None, parent_line_id=section_line_dict["id"], markup="total"
            ),
            "level": section_line_dict["level"]
            if section_line_dict["level"] != 0
            else 1,  # Total line should not be level 0
            "name": _("Total %s", section_line_dict["name"]),
            "parent_id": section_line_dict["id"],
            "unfoldable": False,
            "unfolded": False,
            "caret_options": None,
            "action_id": None,
            # A total is not expandable, so it must not carry the section's expansion
            # handles: they were shipped to the client on every total line of every
            # render, and get_expanded_lines aimed at one raises IndexError.
            "expand_function": None,
            "groupby": None,
            "page_break": False,  # If the section's line possesses a page break, we don't want the total to have it.
        }

    def _split_options_per_column_group(self, options):
        """Get a specific option dict per column group, each enforcing the comparison and horizontal grouping associated
        with the column group. Each of these options dict will contain a new key 'owner_column_group', with the column group key of the
        group it was generated for.

        :param options: The report options upon which the returned options be be based.

        :return:        A dict(column_group_key, options_dict), where column_group_key is the string identifying each column group (the keys
                        of options['column_groups'], and options_dict the generated options for this group.
        """
        options_per_group = {}
        for group_key in options["column_groups"]:
            group_options = self._get_column_group_options(options, group_key)
            options_per_group[group_key] = group_options

        return options_per_group

    @_debug.perf.timed
    def _convert_json_friendly_column_group_totals(
        self,
        json_friendly_column_group_totals,
        expressions_to_exclude=None,
        col_groups_to_exclude=None,
    ):
        """json_friendly_column_group_totals contains ids instead of expressions (because it comes from js) ; this function is used
        to convert them back to records.
        """
        all_column_groups_expression_totals = {}
        for (
            column_group_key,
            expression_totals,
        ) in json_friendly_column_group_totals.items():
            if col_groups_to_exclude and column_group_key in col_groups_to_exclude:
                continue

            all_column_groups_expression_totals[column_group_key] = {}
            for expr_id, expr_totals in expression_totals.items():
                expression = self.env["account.report.expression"].browse(
                    int(expr_id)
                )  # Should already be in cache, so acceptable
                if (
                    not expressions_to_exclude
                    or expression not in expressions_to_exclude
                ):
                    all_column_groups_expression_totals[column_group_key][
                        expression
                    ] = expr_totals

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "column_group_totals_converted",
                report=self,
                column_groups_in=len(json_friendly_column_group_totals),
                column_groups_out=len(all_column_groups_expression_totals),
                expressions=sum(
                    len(expression_totals)
                    for expression_totals in all_column_groups_expression_totals.values()
                ),
                expressions_excluded=len(expressions_to_exclude or ()),
            )
        return all_column_groups_expression_totals

    def _get_json_friendly_column_group_totals(
        self, all_column_groups_expression_totals
    ):
        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = {}
        for (
            column_group_key,
            expressions_totals,
        ) in all_column_groups_expression_totals.items():
            json_friendly_column_group_totals[column_group_key] = {
                expression.id: totals
                for expression, totals in expressions_totals.items()
            }
        return json_friendly_column_group_totals

    def _filter_out_folded_children(self, lines):
        """Returns a list containing all the lines of the provided list that need to be displayed when printing,
        hence removing the children whose parent is folded (especially useful to remove total lines).
        """
        rslt = []
        folded_lines = set()
        for line in lines:
            if line.get("unfoldable") and not line.get("unfolded"):
                folded_lines.add(line["id"])

            if "parent_id" not in line or line["parent_id"] not in folded_lines:
                rslt.append(line)
        return rslt

    def _get_cell_type_value(self, cell):
        if "date" not in cell.get("class", "") or not cell.get("name"):
            # cell is not a date
            return ("text", cell.get("name", ""))
        if isinstance(cell["name"], (float, datetime.date, datetime.datetime)):
            # the date is xlsx compatible
            return ("date", cell["name"])
        try:
            # the date is parsable to a xlsx compatible date
            lg = get_lang(self.env, self.env.user.lang)
            return ("date", datetime.datetime.strptime(cell["name"], lg.date_format))
        except ValueError, TypeError:
            # the date is not parsable thus is returned as text
            return ("text", cell["name"])

    @_debug.perf.timed
    def _get_column_percent_comparison_data(
        self, options, value1, value2, green_on_positive=True
    ):
        """Build the additional percentage column requested by options['column_percent_comparison'].

        Supported comparison types are 'growth', 'budget' and 'analytic_coverage'.

        :param options:             The report options.
        :param value1:              The value in the current period.
        :param value2:              The value in the compared period.
        :param green_on_positive:   A flag customizing the value with a green color depending if the growth is positive.
        :return:                    The column dict to add to line['columns'].
        :rtype:                     dict
        """
        if (
            not isinstance(value1, (int, float))
            or not isinstance(value2, (int, float))
            or float_is_zero(value2, precision_rounding=0.1)
        ):
            return {"name": _("n/a"), "mode": "muted"}

        comparison_type = options["column_percent_comparison"]
        if comparison_type == "growth":
            values_diff = value1 - value2
            growth = round(values_diff / value2 * 100, 1)

            # In case the comparison is made on a negative figure, the color should be the other
            # way around. For example:
            #                       2018         2017           %
            # Product Sales      1000.00     -1000.00     -200.0%
            #
            # The percentage is negative, which is mathematically correct, but my sales increased
            # => it should be green, not red!
            if float_is_zero(growth, 1):
                return {"name": "0.0%", "mode": "muted"}
            else:
                return {
                    "name": f"{float_repr(growth, 1)}%",
                    "mode": "red"
                    if ((values_diff > 0) ^ green_on_positive)
                    else "green",
                }

        elif comparison_type == "budget":
            percentage_value = value1 / value2 * 100
            if float_is_zero(percentage_value, 1):
                # To avoid negative 0
                return {"name": "0.0%", "mode": "green"}

            comparison_value = float_compare(value1, value2, 1)
            return {
                "name": f"{float_repr(percentage_value, 1)}%",
                "mode": "green"
                if (comparison_value >= 0 and green_on_positive)
                or (comparison_value == -1 and not green_on_positive)
                else "red",
            }

        elif comparison_type == "analytic_coverage":
            coverage = round(value1 / value2 * 100, 1)
            if float_is_zero(coverage, precision_rounding=0.1):
                return {"name": "0.0%"}
            else:
                return {
                    "name": str(coverage) + "%",
                    "mode": "green" if float_compare(coverage, 100, 1) == 0 else "red",
                }
        _debug.logic("comparison_type_unsupported", comparison_type=comparison_type)
        return None

    @_debug.perf.timed
    def get_expanded_lines(
        self,
        options,
        line_dict_id,
        groupby,
        expand_function_name,
        progress,
        offset,
        horizontal_split_side,
    ):
        self.env.flush_all()
        self._init_currency_table(options)

        lines = self._expand_unfoldable_line(
            expand_function_name,
            line_dict_id,
            groupby,
            options,
            progress,
            offset,
            horizontal_split_side,
        )
        expanded_count = len(lines)  # debuglog
        lines = self._fully_unfold_lines_if_needed(lines, options)

        if self.allow_account_audit_status_on_lines:
            lines = self._add_account_status_on_lines(lines, options)

        self._update_line_names_for_consolidation(lines)

        if self.custom_handler_model_id:
            lines = self.env[self.custom_handler_model_name]._custom_line_postprocessor(
                self, options, lines
            )

        self._format_column_values(options, lines)
        self._postprocess_chatter_for_annotations(lines)
        _debug.pipeline(
            "expanded_lines_ready",
            report=self,
            line=line_dict_id,
            expand_function=expand_function_name,
            groupby=groupby,
            offset=offset,
            expanded=expanded_count,
            lines=len(lines),
        )
        return lines

    @api.readonly
    def get_expanded_lines_readonly(
        self,
        options,
        line_dict_id,
        groupby,
        expand_function_name,
        progress,
        offset,
        horizontal_split_side,
    ):
        """Readonly version of get_expanded_lines, to be called from RPC when options['readonly_query'] is True,
        to better spread the load on servers when possible.
        """
        return self.get_expanded_lines(
            options,
            line_dict_id,
            groupby,
            expand_function_name,
            progress,
            offset,
            horizontal_split_side,
        )

    @_debug.perf.timed
    def get_annotations(self, options, lines):
        """Return the annotations to display on the report, based on its dates and their display mode.

        :param dict options: options used to generate the report.
        :param list lines: report lines, used to build the domain for the annotations.
        :return: for each annotated line_id, the list of annotations linked to it.
        :rtype: dict
        """
        self.check_singleton()
        annotations_by_line = defaultdict(list)
        line_dict_ids_by_record = defaultdict(set)
        model_ids_map = defaultdict(set)
        for line in lines:
            if line.get("chatter"):
                line_dict_ids_by_record[
                    line["chatter"]["model"], line["chatter"]["id"]
                ].add(line["id"])
                model_ids_map[line["chatter"]["model"]].add(line["chatter"]["id"])

        domain = Domain.OR(
            [
                Domain("message_id.model", "=", model)
                & Domain("message_id.res_id", "in", ids)
                for model, ids in model_ids_map.items()
            ]
        )
        if options.get("date"):
            period_date_from = self._get_annotations_domain_date_from(options)
            period_date_from = self._adjust_date_for_joined_comparison(
                options, period_date_from
            )
            dates_domain = Domain("date", ">=", period_date_from) & Domain(
                "date", "<=", options["date"]["date_to"]
            )
            dates_domain = self._adjust_domain_for_unjoined_comparison(
                options, dates_domain
            )
            domain &= dates_domain

        order = "create_date ASC" if options["export_mode"] else ""
        _debug.logic(
            "annotations_scope_decided",
            report=self,
            models=len(model_ids_map),
            records=len(line_dict_ids_by_record),
            dated=bool(options.get("date")),
            order=order,
        )
        report_annotations = self.env["account.report.annotation"].search(
            domain, order=order
        )
        for annotation in report_annotations:
            message = annotation.message_id
            for line_id in line_dict_ids_by_record[message.model, message.res_id]:
                annotations_by_line[line_id].append(
                    {
                        "id": message.id,
                        "model": message.model,
                        "res_id": message.res_id,
                        "date": annotation.date,
                        "body": message.body,
                        "line_id": line_id,
                    }
                )
        _debug.pipeline(
            "annotations_fetched",
            report=self,
            lines=len(lines),
            annotations=len(report_annotations),
            annotated_lines=len(annotations_by_line),
        )
        return annotations_by_line

    def _get_last_comments_by_line(self, options, lines):
        annotations_by_line = self.get_annotations(options, lines)
        for line, report_annotations in annotations_by_line.items():
            last_annotation = (
                report_annotations[0]["body"] if report_annotations else ""
            )
            annotations_by_line[line] = markupsafe.Markup("<br/>").join(
                html2plaintext(last_annotation).split("\n")
            )
        return annotations_by_line
