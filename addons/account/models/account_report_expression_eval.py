import bisect
import itertools
import re
from ast import literal_eval
from collections import defaultdict, deque
from itertools import chain

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.tools import SQL, Query
from odoo.tools.safe_eval import expr_eval, safe_eval

from .account_report_engine import (
    ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX,
    NO_NEXT_GROUPBY_ENGINES,
)
from odoo.addons.account.models.account_report import (
    ACCOUNT_CODES_ENGINE_SPLIT_REGEX,
    ACCOUNT_CODES_ENGINE_TERM_REGEX,
)

_debug = DebugLog(__name__)


class AccountReportExpressionEval(models.Model):
    _inherit = "account.report"

    @_debug.perf.timed
    def _compute_expression_totals_for_each_column_group(
        self,
        expressions,
        options,
        groupby_to_expand=None,
        forced_all_column_groups_expression_totals=None,
        col_groups_restrict=None,
        offset=0,
        limit=None,
        include_default_vals=False,
        warnings=None,
    ):
        """Main computation function for static lines.

        :param expressions: The account.report.expression objects to evaluate.

        :param options: The options dict for this report, obtained from get_options({}).

        :param groupby_to_expand: The full groupby string for the grouping we want to evaluate. If None, the aggregated value will be computed.
                                  For example, when evaluating a group by partner_id, which further will be divided in sub-groups by account_id,
                                  then id, the full groupby string will be: 'partner_id, account_id, id'.

        :param forced_all_column_groups_expression_totals: The expression totals already computed for this report, to which we will add the
                                                           new totals we compute for expressions (or update the existing ones if some
                                                           expressions are already in forced_all_column_groups_expression_totals). This is
                                                           a dict in the same format as returned by this function.
                                                           This parameter is for example used when adding manual values, where only
                                                           the expressions possibly depending on the new manual value
                                                           need to be updated, while we want to keep all the other values as-is.

        :param col_groups_restrict: List of column group keys of the groups to compute. Other column groups will be ignored, and will
                                    not be added to the result of this function (they can still be provided beforehand through
                                    forced_all_column_groups_expression_totals). If not provided, all colum groups will be computed.

        :param offset: The SQL offset to use when computing the result of these expressions. Used if self.load_more_limit is set, to handle
                       the load more feature.

        :param limit: The SQL limit to apply when computing these expressions' result. Used if self.load_more_limit is set, to handle
                      the load more feature.

        :return: dict(column_group_key, expressions_totals), where:
            - column group key is string identifying each column group in a unique way ; as in options['column_groups']
            - expressions_totals is a dict in the format returned by _compute_expression_totals_for_single_column_group
        """

        def add_expressions_to_groups(
            expressions_to_add, grouped_formulas, force_date_scope=None
        ):
            """Groups the expressions that should be computed together."""
            for expression in expressions_to_add:
                engine = expression.engine

                if engine not in grouped_formulas:
                    grouped_formulas[engine] = {}

                date_scope = (
                    force_date_scope
                    or self._standardize_date_scope_for_date_range(
                        expression.date_scope
                    )
                )
                groupby_data = expression.report_line_id._parse_groupby(
                    options, groupby_to_expand=groupby_to_expand
                )

                next_groupby = (
                    groupby_data["next_groupby"]
                    if engine not in NO_NEXT_GROUPBY_ENGINES
                    else None
                )
                grouping_key = (
                    date_scope,
                    groupby_data["current_groupby"],
                    next_groupby,
                )

                if grouping_key not in grouped_formulas[engine]:
                    grouped_formulas[engine][grouping_key] = {}

                formula = expression.formula

                if (
                    expression.engine == "aggregation"
                    and expression.formula == "sum_children"
                ):
                    formula = " + ".join(
                        f"_expression:{child_expr.id}"
                        for child_expr in expression.report_line_id.children_ids.expression_ids.filtered(
                            lambda e, expression=expression: e.label == expression.label
                        )
                    )

                if formula not in grouped_formulas[engine][grouping_key]:
                    grouped_formulas[engine][grouping_key][formula] = expression
                else:
                    grouped_formulas[engine][grouping_key][formula] |= expression

        if groupby_to_expand and any(
            not expression.report_line_id._get_groupby(options)
            for expression in expressions
        ):
            raise UserError(
                _("Trying to expand groupby results on lines without a groupby value.")
            )

        # Group formulas for batching (when possible)
        grouped_formulas = {}
        if expressions and not include_default_vals:
            expressions = expressions.filtered(
                lambda x: not x.label.startswith("_default")
            )
        for expression in expressions:
            add_expressions_to_groups(expression, grouped_formulas)

            if (
                expression.engine == "aggregation"
                and expression.subformula
                and expression.subformula.startswith("cross_report")
            ):
                # Always expand aggregation expressions, in case their subexpressions are not in expressions parameter
                # (this can happen in cross report, or when auditing an individual aggregation expression)
                expanded_cross = expression._expand_aggregations()
                forced_date_scope = self._standardize_date_scope_for_date_range(
                    expression.date_scope
                )
                add_expressions_to_groups(
                    expanded_cross, grouped_formulas, force_date_scope=forced_date_scope
                )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "formulas_grouped",
                report=self,
                expressions=len(expressions),
                groupby=groupby_to_expand,
                include_default_vals=include_default_vals,
                cross_report_expanded=sum(
                    1
                    for expression in expressions
                    if expression.engine == "aggregation"
                    and expression.subformula
                    and expression.subformula.startswith("cross_report")
                ),
                batches_per_engine={
                    engine: len(batches) for engine, batches in grouped_formulas.items()
                },
                column_groups=len(options.get("column_groups", {})),
                col_groups_restrict=col_groups_restrict,
                forced=bool(forced_all_column_groups_expression_totals),
                offset=offset,
                limit=limit,
            )

        # Treat each formula batch for each column group
        all_column_groups_expression_totals = {}
        # The records a batched domain resolves to depend on the formula alone, never on
        # the column group, the date scope or the period -- so resolve each one once and
        # share the answer across every group instead of re-searching per group.
        batch_ids_cache = {}
        for group_key, group_options in self._split_options_per_column_group(
            options
        ).items():
            if forced_all_column_groups_expression_totals:
                forced_column_group_totals = (
                    forced_all_column_groups_expression_totals.get(group_key, None)
                )
            else:
                forced_column_group_totals = None

            if _debug.logic.enabled and col_groups_restrict:
                _debug.logic(
                    "column_group_restricted",
                    report=self,
                    group_key=group_key,
                    computed=group_key in col_groups_restrict,
                    reused_forced=forced_column_group_totals is not None,
                )
            if not col_groups_restrict or group_key in col_groups_restrict:
                current_group_expression_totals = self._compute_expression_totals_for_single_column_group(
                    group_options,
                    grouped_formulas,
                    forced_column_group_expression_totals=forced_column_group_totals,
                    offset=offset,
                    limit=limit,
                    warnings=warnings,
                    batch_ids_cache=batch_ids_cache,
                )
            else:
                current_group_expression_totals = forced_column_group_totals

            all_column_groups_expression_totals[group_key] = (
                current_group_expression_totals
            )

        _debug.pipeline(
            "column_groups_totals_computed",
            report=self,
            column_groups=len(all_column_groups_expression_totals),
            batch_ids_cached=len(batch_ids_cache),
        )
        return all_column_groups_expression_totals

    @_debug.perf.timed
    def _compute_expression_totals_for_single_column_group(
        self,
        column_group_options,
        grouped_formulas,
        forced_column_group_expression_totals=None,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        """Evaluates expressions for a single column group.

        :param column_group_options: The options dict obtained from _split_options_per_column_group() for the column group to evaluate.

        :param grouped_formulas: A dict(engine, formula_dict), where:
                                 - engine is a string identifying a report engine, in the same format as in account.report.expression's engine
                                   field's technical labels.
                                 - formula_dict is a dict in the same format as _get_formula_batch's formulas_dict parameter,
                                   containing only aggregation formulas.

        :param forced_column_group_expression_totals: The expression totals previously computed, in the same format as this function's result.
                                                      If provided, the result of this function will be an updated version of this parameter,
                                                      recomputing the expressions in grouped_fomulas.

        :param offset: The SQL offset to use when computing the result of these expressions. Used if self.load_more_limit is set, to handle
                       the load more feature.

        :param limit: The SQL limit to apply when computing these expressions' result. Used if self.load_more_limit is set, to handle
                      the load more feature.

        :return: A dict(expression, {'value': value, 'has_sublines': has_sublines}), where:
                 - expression is one of the account.report.expressions that got evaluated

                 - value is the result of that evaluation. Two cases are possible:
                    - if we're evaluating a groupby: value will then be a in the form [(groupby_key, group_val)], where
                        - groupby_key is the key used in the SQL GROUP BY clause to generate this result
                        - group_val: The result computed by the engine for this group. Typically a float.

                    - else: value will directly be the result computed for this expression

                 - has_sublines: [optional key, will default to False if absent]
                                   Whether or not this result corresponds to 1 or more subelements in the database (typically move lines).
                                   This is used to know whether an unfoldable line has results to unfold in the UI.
        """

        def update_expression_totals(
            formula_results,
            column_group_expression_totals,
            cross_report_expression_totals=None,
        ):
            _debug.logic(
                "totals_update",
                report=self,
                results=len(formula_results),
                integer_rounding=column_group_options.get("integer_rounding_enabled"),
                rounding_method=column_group_options.get("integer_rounding"),
                cross_report=cross_report_expression_totals is not None,
            )
            for (_key, expressions), result in formula_results.items():
                for expression in expressions:
                    subformula_error_format = _(
                        'Invalid subformula in expression "%(expression)s" of line "%(line)s": %(subformula)s',
                        expression=expression.label,
                        line=expression.report_line_id.name,
                        subformula=expression.subformula,
                    )
                    if (
                        expression.engine not in ("aggregation", "external")
                        and expression.subformula
                    ):
                        # aggregation subformulas behave differently (cross_report is markup ; if_below, if_above and if_between need evaluation)
                        # They are directly handled in aggregation engine
                        result_value_key = expression.subformula
                    else:
                        result_value_key = "result"

                    # The expression might be signed, so we can't just access the dict key, and directly evaluate it instead.

                    if isinstance(result, list):
                        # Happens when expanding a groupby line, to compute its children.
                        # We then want to keep a list(grouping key, total) as the final result of each total
                        expression_value = []
                        sublines_info = set()
                        for key, result_dict in result:
                            if result_dict.get("has_sublines"):
                                sublines_info.add(key)
                            try:
                                expression_value.append(
                                    (key, safe_eval(result_value_key, result_dict))
                                )
                            except ValueError, SyntaxError:
                                raise UserError(subformula_error_format) from None
                    else:
                        # For non-groupby lines, we directly set the total value for the line.
                        try:
                            expression_value = safe_eval(result_value_key, result)
                            sublines_info = result.get("has_sublines", False)
                        except ValueError, SyntaxError:
                            raise UserError(subformula_error_format) from None

                    if column_group_options.get("integer_rounding_enabled"):
                        in_monetary_column = any(
                            col["expression_label"] == expression.label
                            for col in column_group_options["columns"]
                            if col["figure_type"] == "monetary"
                        )

                        if (
                            in_monetary_column and not expression.figure_type
                        ) or expression.figure_type == "monetary":
                            method = column_group_options["integer_rounding"]
                            if isinstance(expression_value, list):
                                expression_value = [
                                    (
                                        key,
                                        float_round(
                                            value,
                                            precision_digits=0,
                                            rounding_method=method,
                                        )
                                        if value is not None
                                        else value,
                                    )
                                    for key, value in expression_value
                                ]
                            else:
                                expression_value = float_round(
                                    expression_value,
                                    precision_digits=0,
                                    rounding_method=method,
                                )

                    expression_result = {
                        "value": expression_value,
                        "sublines_info": sublines_info,
                    }

                    if expression.report_line_id.report_id == self:
                        if expression in column_group_expression_totals:
                            # This can happen because of a cross report aggregation referencing an expression of its own report,
                            # but forcing a different date_scope onto it. This case is not supported for now ; splitting the aggregation can be
                            # used as a workaround.
                            raise UserError(
                                _(
                                    "Expression labelled '%(label)s' of line '%(line)s' is being overwritten when computing the current report. "
                                    "Make sure the cross-report aggregations of this report only reference terms belonging to other reports.",
                                    label=expression.label,
                                    line=expression.report_line_id.name,
                                )
                            )
                        column_group_expression_totals[expression] = expression_result
                    elif cross_report_expression_totals is not None:
                        # Entering this else means this expression needs to be evaluated because of a cross_report aggregation
                        cross_report_expression_totals[expression] = expression_result

            _debug.pipeline(
                "totals_updated",
                report=self,
                totals=len(column_group_expression_totals),
                cross_report_totals=len(cross_report_expression_totals)
                if cross_report_expression_totals is not None
                else None,
            )

        # Batch each engine that can be
        column_group_expression_totals = (
            dict(forced_column_group_expression_totals)
            if forced_column_group_expression_totals
            else {}
        )
        cross_report_expr_totals_by_scope = {}
        batchable_engines = [
            selection_val[0]
            for selection_val in self.env["account.report.expression"]
            ._fields["engine"]
            .selection
            if selection_val[0] != "aggregation"
        ]
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "column_group_started",
                report=self,
                column_group=column_group_options.get("owner_column_group"),
                date=column_group_options.get("date", {}).get("string"),
                forced_totals=len(column_group_expression_totals),
                batches_per_engine={
                    engine: len(grouped_formulas[engine])
                    for engine in batchable_engines
                    if grouped_formulas.get(engine)
                },
                aggregation_batches=len(grouped_formulas.get("aggregation", {})),
            )
        for engine in batchable_engines:
            for (
                date_scope,
                current_groupby,
                next_groupby,
            ), formulas_dict in grouped_formulas.get(engine, {}).items():
                formula_results = self._get_formula_batch(
                    column_group_options,
                    engine,
                    date_scope,
                    formulas_dict,
                    current_groupby,
                    next_groupby,
                    offset=offset,
                    limit=limit,
                    warnings=warnings,
                    batch_ids_cache=batch_ids_cache,
                )
                update_expression_totals(
                    formula_results,
                    column_group_expression_totals,
                    cross_report_expression_totals=cross_report_expr_totals_by_scope.setdefault(
                        date_scope, {}
                    ),
                )

        # Now that everything else has been computed, resolve aggregation expressions
        # (they can't be treated as the other engines, as if we batch them per date_scope, we'll not be able
        # to compute expressions depending on other expressions with a different date scope).
        aggregation_formulas_dict = {}
        for (
            date_scope,
            _current_groupby,
            _next_groupby,
        ), formulas_dict in grouped_formulas.get("aggregation", {}).items():
            for formula, expressions in formulas_dict.items():
                for expression in expressions:
                    # group_by are ignored by this engine, so we merge every grouped entry into a common dict
                    forced_date_scope = (
                        date_scope
                        if (
                            expression.subformula
                            and expression.subformula.startswith("cross_report")
                        )
                        or expression.report_line_id.report_id != self
                        else None
                    )
                    aggreation_formula_dict_key = (formula, forced_date_scope)
                    aggregation_formulas_dict.setdefault(
                        aggreation_formula_dict_key,
                        self.env["account.report.expression"],
                    )
                    aggregation_formulas_dict[aggreation_formula_dict_key] |= expression

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "aggregations_collected",
                report=self,
                batch_totals=len(column_group_expression_totals),
                cross_report_scopes=len(cross_report_expr_totals_by_scope),
                cross_report_totals=sum(
                    len(scope_totals)
                    for scope_totals in cross_report_expr_totals_by_scope.values()
                ),
                aggregation_formulas=len(aggregation_formulas_dict),
                forced_scope_formulas=sum(
                    1 for _formula, scope in aggregation_formulas_dict if scope
                ),
            )
        if aggregation_formulas_dict:
            aggregation_formula_results = self._get_totals_no_batch_aggregation(
                column_group_options,
                aggregation_formulas_dict,
                column_group_expression_totals,
                cross_report_expr_totals_by_scope,
            )
            update_expression_totals(
                aggregation_formula_results, column_group_expression_totals
            )

        _debug.pipeline(
            "column_group_totals_computed",
            report=self,
            column_group=column_group_options.get("owner_column_group"),
            totals=len(column_group_expression_totals),
        )
        return column_group_expression_totals

    @_debug.perf.timed
    def _get_totals_no_batch_aggregation(
        self,
        column_group_options,
        formulas_dict,
        other_current_report_expr_totals,
        other_cross_report_expr_totals_by_scope,
    ):
        """Computes expression totals for 'aggregation' engine, after all other engines have been evaluated.

        :param column_group_options: The options for the column group being evaluated, as obtained from _split_options_per_column_group.

        :param formulas_dict: A dict {(formula, forced_date_scope): expressions}, containing only aggregation formulas.
                              forced_date_scope will only be set in case of cross_report expressions. Else, it will be None

        :param other_current_report_expr_totals: The expressions_totals obtained after computing all non-aggregation engines, for the expressions
                                                 belonging directly to self (so, not the ones referenced by a cross_report aggreation).
                                                 This is a dict in the same format as _compute_expression_totals_for_single_column_group's result
                                                 (the only difference being it does not contain any aggregation expression yet).

        :param other_cross_report_expr_totals_by_scope: A dict(forced_date_scope, expression_totals), where expression_totals is in the same form as
                                               _compute_expression_totals_for_single_column_group's result. This parameter contains the results
                                               of the non-aggregation expressions used by cross_report expressions ; they all belong to different
                                               reports than self. The forced_date_scope corresponds to the original date_scope set on the
                                               cross_report expression referencing them. The same expressions can be referenced multiple times
                                               under different date scopes.

        :return : A dict((formula, expressions), result), where result is in the form {'result': numeric_value}
        """

        def _resolve_subformula_on_dict(result, line_codes_expression_map, subformula):
            split_subformula = subformula.split(".")
            if len(split_subformula) > 1:
                line_code, expression_label = split_subformula
                return result[line_codes_expression_map[line_code][expression_label]]

            if subformula.startswith("_expression:"):
                expression_id = int(subformula.split(":")[1])
                return result[expression_id]

            # Wrong subformula; the KeyError is caught in the function below
            raise KeyError

        def _is_float(to_test):
            try:
                float(to_test)
                return True
            except ValueError:
                return False

        def add_expression_to_map(
            expression,
            expression_res,
            figure_types_cache,
            current_report_eval_dict,
            current_report_codes_map,
            other_reports_eval_dict,
            other_reports_codes_map,
            cross_report=False,
        ):
            """Process an expression and its result, updating the evaluation dicts and code maps in place.

            :param expression: the account.report.expression to process.
            :param dict expression_res: the result computed for that expression.
            :param dict figure_types_cache: {report: {label: figure_type}}.
            :param dict current_report_eval_dict: {expression_id: value}.
            :param dict current_report_codes_map: {line_code: {expression_label: expression_id}}.
            :param dict other_reports_eval_dict: {forced_date_scope: {expression_id: value}}.
            :param dict other_reports_codes_map: {forced_date_scope: {line_code: {expression_label: expression_id}}}.
            :param bool cross_report: whether a cross_report expression is being processed.
            """

            expr_report = expression.report_line_id.report_id
            report_default_figure_types = figure_types_cache.setdefault(expr_report, {})
            expression_label = report_default_figure_types.get(
                expression.label, "_not_in_cache"
            )
            if expression_label == "_not_in_cache":
                report_default_figure_types[expression.label] = (
                    expr_report.column_ids.filtered(
                        lambda x: x.expression_label == expression.label
                    ).figure_type
                )

            default_figure_type = figure_types_cache[expr_report][expression.label]
            figure_type = expression.figure_type or default_figure_type
            value = expression_res["value"]
            if figure_type == "monetary" and value:
                value = self.env.company.currency_id.round(value)

            if cross_report:
                other_reports_eval_dict.setdefault(forced_date_scope, {})[
                    expression.id
                ] = value
            else:
                current_report_eval_dict[expression.id] = value

        current_report_eval_dict = {}  # {expression_id: value}
        other_reports_eval_dict = {}  # {forced_date_scope: {expression_id: value}}
        current_report_codes_map = {}  # {line_code: {expression_label: expression_id}}
        other_reports_codes_map = {}  # {forced_date_scope: {line_code: {expression_label: expression_id}}}

        figure_types_cache = {}  # {report : {label: figure_type}}
        for expression, expression_res in other_current_report_expr_totals.items():
            add_expression_to_map(
                expression,
                expression_res,
                figure_types_cache,
                current_report_eval_dict,
                current_report_codes_map,
                other_reports_eval_dict,
                other_reports_codes_map,
            )
            if expression.report_line_id.code:
                current_report_codes_map.setdefault(expression.report_line_id.code, {})[
                    expression.label
                ] = expression.id

        for (
            forced_date_scope,
            scope_expr_totals,
        ) in other_cross_report_expr_totals_by_scope.items():
            for expression, expression_res in scope_expr_totals.items():
                add_expression_to_map(
                    expression,
                    expression_res,
                    figure_types_cache,
                    current_report_eval_dict,
                    current_report_codes_map,
                    other_reports_eval_dict,
                    other_reports_codes_map,
                    True,
                )
                if expression.report_line_id.code:
                    other_reports_codes_map.setdefault(
                        forced_date_scope, {}
                    ).setdefault(expression.report_line_id.code, {})[
                        expression.label
                    ] = expression.id

        # Complete current_report_eval_dict with the formulas of uncomputed aggregation lines
        aggregations_terms_to_evaluate = set()  # Those terms are part of the formulas to evaluate; we know they will get a value eventually
        for (formula, forced_date_scope), expressions in formulas_dict.items():
            for expression in expressions:
                aggregations_terms_to_evaluate.add(
                    f"_expression:{expression.id}"
                )  # In case it needs to be called by sum_children

                if expression.report_line_id.code:
                    if expression.report_line_id.report_id == self:
                        current_report_codes_map.setdefault(
                            expression.report_line_id.code, {}
                        )[expression.label] = expression.id
                    else:
                        other_reports_codes_map.setdefault(
                            forced_date_scope, {}
                        ).setdefault(expression.report_line_id.code, {})[
                            expression.label
                        ] = expression.id

                    aggregations_terms_to_evaluate.add(
                        f"{expression.report_line_id.code}.{expression.label}"
                    )

                    if not expression.subformula:
                        # Expressions with bounds cannot be replaced by their formula in formulas calling them (otherwize, bounds would be ignored).
                        # Same goes for cross_report, otherwise the forced_date_scope will be ignored, leading to an impossibility to get evaluate the expression.
                        if expression.report_line_id.report_id == self:
                            eval_dict = current_report_eval_dict
                        else:
                            eval_dict = other_reports_eval_dict.setdefault(
                                forced_date_scope, {}
                            )

                        eval_dict[expression.id] = formula

        rslt = {}
        to_treat = deque(
            (formula, formula, forced_date_scope)
            for (formula, forced_date_scope) in formulas_dict
        )  # Formed like [(expanded formula, original unexpanded formula)]
        term_separator_regex = r"(?<!\de)[+-]|[ ()/*]"
        term_replacement_regex = r"(^|(?<=[ ()+/*-]))%s((?=[ ()+/*-])|$)"
        # A formula is requeued whenever a term it references is not computable yet. Two
        # aggregations referencing each other therefore expand into one another forever,
        # each round growing the formula instead of reducing it, with nothing to stop it.
        # Every honest round consumes at least one distinct aggregation term, so needing
        # more rounds than there are terms and formulas means the references form a cycle.
        max_expansion_rounds = (
            len(aggregations_terms_to_evaluate) + len(formulas_dict) + 1
        )
        expansion_rounds = defaultdict(int)
        _debug.pipeline(
            "aggregation_maps_built",
            report=self,
            formulas=len(formulas_dict),
            current_values=len(current_report_eval_dict),
            current_codes=len(current_report_codes_map),
            cross_report_scopes=len(other_reports_eval_dict),
            terms_to_evaluate=len(aggregations_terms_to_evaluate),
            max_expansion_rounds=max_expansion_rounds,
        )
        while to_treat:
            formula, unexpanded_formula, forced_date_scope = to_treat.popleft()

            expansion_rounds[unexpanded_formula, forced_date_scope] += 1
            if (
                expansion_rounds[unexpanded_formula, forced_date_scope]
                > max_expansion_rounds
            ):
                _debug.logic(
                    "cyclic_aggregation_detected",
                    report=self,
                    formula=unexpanded_formula,
                    date_scope=forced_date_scope,
                    max_expansion_rounds=max_expansion_rounds,
                )
                raise UserError(
                    _(
                        "Cyclic aggregation: %(expressions)s cannot be computed, because its formula %(formula)s references expressions that reference it back.",
                        expressions=", ".join(
                            sorted(
                                f"{expression.report_line_name} > {expression.label}"
                                for expression in formulas_dict[
                                    unexpanded_formula, forced_date_scope
                                ]
                            )
                        ),
                        formula=unexpanded_formula,
                    )
                )

            full_eval_dict = {
                **current_report_eval_dict,
                **other_reports_eval_dict.get(forced_date_scope, {}),
            }
            full_codes_map = {
                **current_report_codes_map,
                **other_reports_codes_map.get(forced_date_scope, {}),
            }

            # Evaluate the formula
            terms_to_eval = [
                term
                for term in re.split(term_separator_regex, formula)
                if term and not _is_float(term)
            ]
            if terms_to_eval:
                # The formula can't be evaluated as-is. Replace the terms by their value or formula,
                # and enqueue the formula back; it'll be tried anew later in the loop.
                for term in terms_to_eval:
                    try:
                        expanded_term = _resolve_subformula_on_dict(
                            full_eval_dict,
                            full_codes_map,
                            term,
                        )
                    except KeyError:
                        if term in aggregations_terms_to_evaluate:
                            # Then, the term is probably an aggregation with bounds that still needs to be computed. We need to keep on looping
                            continue
                        _debug.logic(
                            "term_unresolvable",
                            report=self,
                            term=term,
                            formula=unexpanded_formula,
                            date_scope=forced_date_scope,
                        )
                        raise UserError(
                            _(
                                "Could not expand term %(term)s while evaluating formula %(unexpanded_formula)s",
                                term=term,
                                unexpanded_formula=unexpanded_formula,
                            )
                        ) from None

                    formula = re.sub(
                        term_replacement_regex % re.escape(term),
                        f"({expanded_term})",
                        formula,
                    )
                to_treat.append((formula, unexpanded_formula, forced_date_scope))

            else:
                # The formula contains only digits and operators; it can be evaluated
                try:
                    formula_result = expr_eval(formula)
                except ZeroDivisionError:
                    for expr in formulas_dict[unexpanded_formula, forced_date_scope]:
                        if expr.subformula != "ignore_zero_division":
                            raise UserError(
                                _(
                                    "Division by zero occurred while evaluating Expression: %(line_name)s > %(label)s.",
                                    line_name=expr.report_line_name,
                                    label=expr.label,
                                )
                            ) from None
                    _debug.logic(
                        "zero_division_ignored",
                        report=self,
                        formula=unexpanded_formula,
                        date_scope=forced_date_scope,
                    )
                    # Arbitrary choice; for clarity of the report. A 0 division could typically happen when there is no result in the period.
                    formula_result = 0

                for expression in formulas_dict[
                    (unexpanded_formula, forced_date_scope)
                ]:
                    # Apply subformula
                    if expression.subformula and expression.subformula.startswith(
                        "if_other_expr_"
                    ):
                        other_expr_criterium_match = re.match(
                            r"^(?P<criterium>\w+)\("
                            r"(?P<line_code>\w+)[.](?P<expr_label>\w+),[ ]*"
                            r"(?P<bound_params>.*)\)$",
                            expression.subformula,
                        )
                        if not other_expr_criterium_match:
                            raise UserError(
                                _(
                                    "Wrong format for if_other_expr_above/if_other_expr_below formula: %s",
                                    expression.subformula,
                                )
                            )

                        criterium_code = other_expr_criterium_match["line_code"]
                        criterium_label = other_expr_criterium_match["expr_label"]
                        criterium_expression_id = full_codes_map.get(
                            criterium_code, {}
                        ).get(criterium_label)
                        criterium_val = full_eval_dict.get(criterium_expression_id)

                        if not criterium_expression_id:
                            raise UserError(
                                _(
                                    "This subformula references an unknown expression: %s",
                                    expression.subformula,
                                )
                            )

                        if not isinstance(criterium_val, (float, int)):
                            # The criterium expression has not be evaluated yet. Postpone the evaluation of this formula, and skip this expression
                            # for now. We still try to evaluate other expressions using this formula if any; this means those expressions will
                            # be processed a second time later, giving the same result. This is a rare corner case, and not so costly anyway.
                            _debug.logic(
                                "other_expr_criterium_postponed",
                                report=self,
                                expression=expression,
                                criterium_code=criterium_code,
                                criterium_label=criterium_label,
                            )
                            to_treat.append(
                                (formula, unexpanded_formula, forced_date_scope)
                            )
                            continue

                        bound_subformula = other_expr_criterium_match[
                            "criterium"
                        ].replace(
                            "other_expr_", ""
                        )  # e.g. 'if_other_expr_above' => 'if_above'
                        bound_params = other_expr_criterium_match["bound_params"]
                        bounded_value = self._aggregation_apply_bounds(
                            column_group_options,
                            f"{bound_subformula}({bound_params})",
                            criterium_val,
                        )
                        expression_result = formula_result * int(
                            bool(bounded_value is not None)
                        )
                    else:
                        expression_result = (
                            self._aggregation_apply_bounds(
                                column_group_options,
                                expression.subformula,
                                formula_result,
                            )
                            or 0
                        )

                    if column_group_options.get("integer_rounding_enabled"):
                        expression_result = float_round(
                            expression_result,
                            precision_digits=0,
                            rounding_method=column_group_options["integer_rounding"],
                        )

                    # Store result
                    standardized_expression_scope = (
                        self._standardize_date_scope_for_date_range(
                            expression.date_scope
                        )
                    )
                    if (
                        forced_date_scope == standardized_expression_scope
                        or not forced_date_scope
                    ) and expression.report_line_id.report_id == self:
                        # This condition ensures we don't return necessary subcomputations in the final result
                        rslt[(unexpanded_formula, expression)] = {
                            "result": expression_result
                        }

                    # Handle recursive aggregations (explicit or through the sum_children shortcut).
                    # We need to make the result of our computation available to other aggregations, as they are still waiting in to_treat to be evaluated.
                    if expression.report_line_id.report_id == self:
                        current_report_eval_dict[expression.id] = expression_result
                    else:
                        other_reports_eval_dict.setdefault(forced_date_scope, {})[
                            expression.id
                        ] = expression_result

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "aggregations_resolved",
                report=self,
                results=len(rslt),
                rounds=sum(expansion_rounds.values()),
                deepest_rounds=max(expansion_rounds.values(), default=0),
                integer_rounding=column_group_options.get("integer_rounding_enabled"),
            )
        return rslt

    @_debug.perf.timed
    def _aggregation_apply_bounds(
        self, column_group_options, subformula, unbounded_value
    ):
        """Applies the bounds of the provided aggregation expression to an unbounded value that got computed for it and returns the result.
        Bounds can be defined as subformulas of aggregation expressions, with the following possible values:

            - if_above(CUR(bound_value)):
                                    => Result will be None if it's <= the provided bound value; else it'll be unbounded_value

            - if_below(CUR(bound_value)):
                                    => Result will be None if it's >= the provided bound value; else it'll be unbounded_value

            - if_between(CUR(bound_value1), CUR(bound_value2)):
                                    => Result will be None if it isn't between the provided bound values, both included; else it'll be unbounded_value

            - round(decimal_places, rounding_method):
                                    => Result will be the rounded unbounded_value.

            (where CUR is a currency code, and bound_value* are float amounts in CUR currency)
        """
        if not subformula:
            return unbounded_value

        # So an expression can't have bounds and be cross_reports, for simplicity.
        # To do that, just split the expression in two parts.
        if subformula and subformula.startswith("round"):
            matches = re.match(
                r"round\((?P<precision>-?\d+)(,\s*(?P<rounding_method>(HALF-UP|HALF-DOWN|HALF-EVEN|UP|DOWN)))?\)",
                subformula.replace(" ", ""),
            )
            if not matches:
                raise UserError(
                    _(
                        "Invalid rounding subformula: %(subformula)s. Expected round(decimal_places) or round(decimal_places, ROUNDING-METHOD), with a method among HALF-UP, HALF-DOWN, HALF-EVEN, UP, DOWN.",
                        subformula=subformula,
                    )
                )
            precision = int(matches["precision"])
            rounding_method = matches["rounding_method"] or "HALF-DOWN"
            _debug.logic(
                "rounding_subformula_applied",
                report=self,
                precision=precision,
                rounding_method=rounding_method,
                negative_precision=precision < 0,
            )
            # We support rounding with a negative amount, similarly to how it works with python's round method.
            # As we also want to support using a rounding method, we will play a bit with the number and round using float_round
            if precision < 0:
                precision_power = abs(precision)
                unbounded_value /= 10**precision_power
                unbounded_value = float_round(
                    unbounded_value, precision_digits=0, rounding_method=rounding_method
                )
                return unbounded_value * (10**precision_power)
            else:
                return float_round(
                    unbounded_value,
                    precision_digits=precision,
                    rounding_method=rounding_method,
                )

        if subformula != "ignore_zero_division" and not subformula.startswith(
            "cross_report"
        ):
            company_currency = self.env.company.currency_id
            date_to = column_group_options["date"]["date_to"]

            match = re.match(
                r"(?P<criterium>\w*)"
                r"\((?P<currency_1>[A-Z]{3})\((?P<amount_1>[-]?\d+(\.\d+)?)\)"
                r"(,(?P<currency_2>[A-Z]{3})\((?P<amount_2>[-]?\d+(\.\d+)?)\))?\)$",
                subformula.replace(" ", ""),
            )
            if not match:
                raise UserError(
                    _(
                        "Invalid bound subformula: %(subformula)s. Expected if_above(CUR(amount)), if_below(CUR(amount)) or if_between(CUR(amount), CUR(amount)), with CUR an upper-case currency code.",
                        subformula=subformula,
                    )
                )
            group_values = match.groupdict()

            # Convert the provided bounds into company currency
            currency_code_1 = group_values.get("currency_1")
            currency_code_2 = group_values.get("currency_2")
            currency_codes = [
                currency_code
                for currency_code in [currency_code_1, currency_code_2]
                if currency_code and currency_code != company_currency.name
            ]

            if currency_codes:
                currencies = (
                    self.env["res.currency"]
                    .with_context(active_test=False)
                    .search([("name", "in", currency_codes)])
                )
                # A code that matches no record would otherwise skip conversion
                # silently and compare the literal amount against a value in
                # company currency -- the bound would just mean something else.
                missing_codes = set(currency_codes) - set(currencies.mapped("name"))
                if missing_codes:
                    raise UserError(
                        _(
                            "Unknown currency code in bound subformula %(subformula)s: %(codes)s.",
                            subformula=subformula,
                            codes=", ".join(sorted(missing_codes)),
                        )
                    )
            else:
                currencies = self.env["res.currency"]

            amount_1 = float(group_values["amount_1"] or 0)
            amount_2 = float(group_values["amount_2"] or 0)
            for currency in currencies:
                if currency != company_currency:
                    if currency.name == currency_code_1:
                        amount_1 = currency._convert(
                            amount_1, company_currency, self.env.company, date_to
                        )
                    if amount_2 and currency.name == currency_code_2:
                        amount_2 = currency._convert(
                            amount_2, company_currency, self.env.company, date_to
                        )

            # Evaluate result
            criterium = group_values["criterium"]
            _debug.logic(
                "bound_evaluated",
                report=self,
                criterium=criterium,
                value=unbounded_value,
                amount_1=amount_1,
                amount_2=amount_2,
                converted_currencies=currency_codes,
            )
            if criterium == "if_below":
                if company_currency.compare_amounts(unbounded_value, amount_1) >= 0:
                    _debug.logic("below_bound_suppressed", report=self)
                    return None
            elif criterium == "if_above":
                if company_currency.compare_amounts(unbounded_value, amount_1) <= 0:
                    _debug.logic("above_bound_suppressed", report=self)
                    return None
            elif criterium == "if_between":
                if (
                    company_currency.compare_amounts(unbounded_value, amount_1) < 0
                    or company_currency.compare_amounts(unbounded_value, amount_2) > 0
                ):
                    _debug.logic("between_bound_suppressed", report=self)
                    return None
            else:
                raise UserError(_("Unknown bound criterium: %s", criterium))

        return unbounded_value

    @_debug.perf.timed
    def _get_formula_batch(
        self,
        column_group_options,
        formula_engine,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        """Evaluates a batch of formulas.

        :param column_group_options: The options for the column group being evaluated, as obtained from _split_options_per_column_group.

        :param formula_engine: A string identifying a report engine. Must be one of account.report.expression's engine field's technical labels.

        :param date_scope: The date_scope under which to evaluate the fomulas. Must be one of account.report.expression's date_scope field's
                           technical labels.

        :param formulas_dict: A dict in the dict(formula, expressions), where:
                                - formula: a formula to be evaluated with the engine referred to by parent dict key
                                - expressions: a recordset of all the expressions to evaluate using formula (possibly with distinct subformulas)

        :param current_groupby: The groupby to evaluate, or None if there isn't any. In case of multi-level groupby, only contains the element
                                that needs to be computed (so, if unfolding a line doing 'partner_id,account_id,id'; current_groupby will only be
                                'partner_id'). Subsequent groupby will be in next_groupby.

        :param next_groupby: Full groupby string of the groups that will have to be evaluated next for these expressions, or None if there isn't any.
                             For example, in the case depicted in the example of current_groupby, next_groupby will be 'account_id,id'.

        :param offset: The SQL offset to use when computing the result of these expressions.

        :param limit: The SQL limit to apply when computing these expressions' result.

        :return: The result might have two different formats depending on the situation:
            - if we're computing a groupby: {(formula, expressions): [(grouping_key, {'result': value, 'has_sublines': boolean}), ...], ...}
            - if we're not: {(formula, expressions): {'result': value, 'has_sublines': boolean}, ...}
            'result' key is the default; different engines might use one or multiple other keys instead, depending of the subformulas they allow
            (e.g. 'sum', 'sum_if_pos', ...)
        """
        engine_function_name = f"_get_formula_batch_with_engine_{formula_engine}"
        with _debug.perf(
            "_get_formula_batch",
            cr=self.env.cr,
            report=self,
            engine=formula_engine,
            scope=date_scope,
            formulas=len(formulas_dict),
            groupby=current_groupby,
        ):
            return getattr(self, engine_function_name)(
                column_group_options,
                date_scope,
                formulas_dict,
                current_groupby,
                next_groupby,
                offset=offset,
                limit=limit,
                warnings=warnings,
                batch_ids_cache=batch_ids_cache,
            )

    @_debug.perf.timed
    def _get_formula_batch_with_engine_tax_tags(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        """Report engine.

        The formulas made for this report simply consist of a tag label. When an expression using this engine is created, it also creates one
        account.account.tag object, where the tag name is the chosen formula striped of the sign. The balance of the expressions using this engine is
        computed by gathering all the move lines using their tags, and applying the sign of their tag to their balance.

        This engine does not support any subformula.
        """
        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )
        all_expressions = self.env["account.report.expression"]
        for expressions in formulas_dict.values():
            all_expressions |= expressions
        tags = all_expressions._get_matching_tags()
        _debug.pipeline(
            "tax_tags_matched",
            report=self,
            date_scope=date_scope,
            formulas=len(formulas_dict),
            expressions=len(all_expressions),
            tags=len(tags),
            groupby=current_groupby,
            offset=offset,
            limit=limit,
        )

        query = self._get_report_query(options, date_scope)
        groupby_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, query
            )
            if current_groupby
            else None
        )
        tail_query = self._get_engine_query_tail(offset, limit)
        acc_tag_name = (
            self.with_context(lang="en_US")
            .env["account.account.tag"]
            ._field_to_sql("acc_tag", "name")
        )
        sql = SQL(
            """
            SELECT
                %(acc_tag_name)s AS formula,
                SUM(%(balance_select)s) AS balance,
                COUNT(account_move_line.id) AS aml_count
                %(select_groupby_sql)s

            FROM %(table_references)s

            JOIN account_account_tag_account_move_line_rel aml_tag
                ON aml_tag.account_move_line_id = account_move_line.id
            JOIN account_account_tag acc_tag
                ON aml_tag.account_account_tag_id = acc_tag.id
            %(currency_table_join)s

            WHERE %(search_condition)s
              AND aml_tag.account_account_tag_id IN %(tag_ids)s

            GROUP BY %(groupby_clause)s

            ORDER BY %(groupby_clause)s

            %(tail_query)s
            """,
            acc_tag_name=acc_tag_name,
            select_groupby_sql=SQL(", %s AS grouping_key", groupby_sql)
            if groupby_sql
            else SQL(),
            table_references=query.from_clause,
            tag_ids=tuple(tags.ids),
            balance_select=self._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            currency_table_join=self._currency_table_aml_join(options),
            search_condition=query.where_clause,
            # Ordinals, not the alias and not the expression: the joins can carry
            # a `formula` column (account_tax has one) and PostgreSQL resolves a
            # GROUP BY name to an input column first, while the expression holds
            # a bound parameter, so a second spelling of it is a second parameter.
            groupby_clause=SQL("1, 4") if groupby_sql else SQL("1"),
            tail_query=tail_query,
        )

        rslt = {
            (formula_str.lstrip("-"), formula_expr): []
            if current_groupby
            else {"result": 0, "has_sublines": False}
            for formula_str, formula_expr in formulas_dict.items()
        }
        tag_rows = 0  # debuglog
        for tax_tag, balance, aml_count, *grouping_key in self.env.execute_query(sql):
            tag_rows += 1  # debuglog
            if expression := formulas_dict.get(f"-{tax_tag}"):
                balance *= -1
            else:
                expression = formulas_dict[tax_tag]
            rslt_dict = {"result": balance, "has_sublines": aml_count > 0}
            if current_groupby:
                rslt[tax_tag, expression].append((grouping_key[0], rslt_dict))
            else:
                rslt[tax_tag, expression] = rslt_dict
        _debug.perf.count("tax_tag_rows_fetched", rows=tag_rows)

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "tax_tags_results",
                report=self,
                results=len(rslt),
                groups=sum(len(v) for v in rslt.values() if isinstance(v, list))
                if current_groupby
                else None,
            )
        return rslt

    @_debug.perf.timed
    def _get_formula_batch_with_engine_domain(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        """Report engine.

        Formulas made for this engine consist of a domain on account.move.line. Only those move lines will be used to compute the result.

        This engine supports a few subformulas, each returning a slighlty different result:
        - sum: the result will be sum of the matched move lines' balances

        - sum_if_pos: the result will be the same as sum only if it's positive; else, it will be 0

        - sum_if_neg: the result will be the same as sum only if it's negative; else, it will be 0

        - count_rows: the result will be the number of sublines this expression has. If the parent report line has no groupby,
                      then it will be the number of matching amls. If there is a groupby, it will be the number of distinct grouping
                      keys at the first level of this groupby (so, if groupby is 'partner_id, account_id', the number of partners).
        """

        def _format_result_depending_on_groupby(formula_rslt):
            if not current_groupby:
                if formula_rslt:
                    # There should be only one element in the list; we only return its totals (a dict) ; so that a list is only returned in case
                    # of a groupby being unfolded.
                    return formula_rslt[0][1]
                else:
                    # No result at all
                    return {
                        "sum": 0,
                        "sum_if_pos": 0,
                        "sum_if_neg": 0,
                        "count_rows": 0,
                        "has_sublines": False,
                    }
            return formula_rslt

        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )

        batchable_domains_data = {}  # In the form {(model name, aml_field):  [(domain, expressions)]}
        non_batchable_domains_data = []  # In the form [(domain, expressions)]
        for formula, expressions in formulas_dict.items():
            try:
                domain = literal_eval(formula)
            except ValueError, SyntaxError:
                raise UserError(
                    _(
                        'Invalid domain formula in expression "%(expression)s" of line "%(line)s": %(formula)s',
                        expression=expressions[0].label,
                        line=expressions[0].report_line_id.name,
                        formula=formula,
                    )
                ) from None

            if (
                offset
                or limit
                or any(expr.subformula == "count_rows" for expr in expressions)
            ):
                # count_rows cannot be computed generically with batching (because of the additional groupby we inject in the batch computation)
                non_batchable_domains_data.append((domain, formula, expressions))
                continue

            aml_root_fields = set()
            traversing_model_domain = []
            batchable = True
            for term in domain:
                match term:
                    case (aml_field_expr, operator, value):
                        aml_field, _dot, model_field_expr = aml_field_expr.partition(
                            "."
                        )
                        aml_root_fields.add(aml_field)
                        if not model_field_expr and not self._is_id_positive_condition(
                            operator, value
                        ):
                            # Rewriting a bare many2one condition into a condition on the
                            # comodel's id only preserves its meaning for a positive match
                            # on ids. Every other operator either means something else on a
                            # many2one (like/ilike match display_name) or must also match the
                            # rows where the foreign key is NULL, which a search on the
                            # comodel can never return.
                            batchable = False
                        traversing_model_domain.append(
                            (model_field_expr or "id", operator, value)
                        )
                    case str():
                        traversing_model_domain.append(term)

            if batchable and len(aml_root_fields) == 1:
                aml_field = self.env["account.move.line"]._fields[
                    next(iter(aml_root_fields))
                ]
                if aml_field.type == "many2one":
                    batchable_domains_data.setdefault(
                        (aml_field.comodel_name, aml_field.name), []
                    ).append((traversing_model_domain, formula, expressions))
                else:
                    non_batchable_domains_data.append((domain, formula, expressions))
            else:
                non_batchable_domains_data.append((domain, formula, expressions))

        if _debug.logic.enabled:
            _debug.logic(
                "domains_batched",
                report=self,
                date_scope=date_scope,
                groupby=current_groupby,
                next_groupby=next_groupby,
                formulas=len(formulas_dict),
                batches=sorted(
                    f"{model}.{field}:{len(domains)}"
                    for (model, field), domains in batchable_domains_data.items()
                ),
                non_batchable=len(non_batchable_domains_data),
                paginated=bool(offset or limit),
            )

        rslt = {}
        for (batch_model, batch_aml_field), batch_domains in chain(
            batchable_domains_data.items(),
            (((None, None), [data]) for data in non_batchable_domains_data),
        ):
            aml_domain = (
                batch_domains[0][0] if not batch_model else None
            )  # batch_domains contains only one element if there is not batch_model/batch_aml_field
            query = self._get_report_query(options, date_scope, domain=aml_domain)

            groupby_sql = (
                self.env["account.move.line"]._field_to_sql(
                    "account_move_line", current_groupby, query
                )
                if current_groupby
                else None
            )
            batch_groupby_sql = (
                self.env["account.move.line"]._field_to_sql(
                    "account_move_line", batch_aml_field, query
                )
                if batch_aml_field
                else None
            )

            select_count_field = self.env["account.move.line"]._field_to_sql(
                "account_move_line",
                next_groupby.split(",")[0] if next_groupby else "id",
                query,
            )

            tail_query = self._get_engine_query_tail(offset, limit)
            query = SQL(
                """
                SELECT
                    COALESCE(SUM(%(balance_select)s), 0.0) AS sum,
                    %(count_rows_select)s AS count_rows
                    %(select_groupby_sql)s
                    %(select_batch_groupby_sql)s
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                %(groupby_sql)s
                %(order_by_sql)s
                %(tail_query)s
                """,
                count_rows_select=SQL(
                    # SQL COUNT skips NULLs, but a NULL grouping key is a real group
                    # (rendered as "Unknown" when the line is expanded), so it has to be
                    # counted as one.
                    "COUNT(DISTINCT %(field)s) + (CASE WHEN COUNT(*) FILTER (WHERE %(field)s IS NULL) > 0 THEN 1 ELSE 0 END)",
                    field=select_count_field,
                ),
                select_groupby_sql=SQL(", %s AS grouping_key", groupby_sql)
                if groupby_sql
                else SQL(),
                select_batch_groupby_sql=SQL(
                    ", %s AS batch_grouping_key", batch_groupby_sql
                )
                if batch_groupby_sql
                else SQL(),
                table_references=query.from_clause,
                balance_select=self._currency_table_apply_rate(
                    SQL("account_move_line.balance")
                ),
                currency_table_join=self._currency_table_aml_join(options),
                search_condition=query.where_clause,
                groupby_sql=SQL(
                    "GROUP BY %s",
                    SQL(",").join(
                        groupby_term
                        for groupby_term in (groupby_sql, batch_groupby_sql)
                        if groupby_term
                    ),
                )
                if groupby_sql or batch_groupby_sql
                else SQL(),
                order_by_sql=SQL(" ORDER BY %s", groupby_sql) if groupby_sql else SQL(),
                tail_query=tail_query,
            )

            self.env.cr.execute(query)
            all_query_res = self.env.cr.dictfetchall()
            _debug.perf.count(
                "domain_rows_fetched",
                report=self,
                batch_model=batch_model,
                batch_field=batch_aml_field,
                domains=len(batch_domains),
                rows=len(all_query_res),
            )

            results_by_batch_grouping_key = {}
            if batch_model:
                for query_res in all_query_res:
                    results_by_batch_grouping_key.setdefault(
                        query_res["batch_grouping_key"], []
                    ).append(query_res)

            for domain, formula, expressions in batch_domains:
                formula_rslt = []
                total_sum = 0
                totals_by_grouping_key = {}

                batch_included_ids = self._get_batch_model_ids(
                    batch_model, domain, batch_ids_cache
                )
                for batch_included_id in batch_included_ids:
                    batch_res = (
                        results_by_batch_grouping_key.get(batch_included_id, [])
                        if batch_included_id is not None
                        else all_query_res
                    )

                    for query_res in batch_res:
                        totals = totals_by_grouping_key.setdefault(
                            query_res.get("grouping_key"),
                            {
                                "sum": 0,
                                "sum_if_pos": 0,
                                "sum_if_neg": 0,
                                "count_rows": 0,
                                "has_sublines": False,
                            },
                        )

                        res_sum = query_res["sum"]
                        totals["sum"] += res_sum
                        totals["count_rows"] += query_res["count_rows"]
                        totals["has_sublines"] = totals["has_sublines"] or bool(
                            query_res["count_rows"]
                        )

                        total_sum += res_sum

                for grouping_key, totals in totals_by_grouping_key.items():
                    formula_rslt.append((grouping_key, totals))

                # Handle sum_if_pos, -sum_if_pos, sum_if_neg and -sum_if_neg
                expressions_by_sign_policy = defaultdict(
                    lambda: self.env["account.report.expression"]
                )
                for expression in expressions:
                    subformula_without_sign = expression.subformula.replace(
                        "-", ""
                    ).strip()
                    if subformula_without_sign in ("sum_if_pos", "sum_if_neg"):
                        expressions_by_sign_policy[subformula_without_sign] += (
                            expression
                        )
                    else:
                        expressions_by_sign_policy["no_sign_check"] += expression

                # Then we have to check the total of the line and only give results if its sign matches the desired policy.
                # This is important for groupby managements, for which we can't just check the sign query_res by query_res
                if (
                    expressions_by_sign_policy["sum_if_pos"]
                    or expressions_by_sign_policy["sum_if_neg"]
                ):
                    sign_policy_with_value = (
                        "sum_if_pos"
                        if self.env.company.currency_id.compare_amounts(total_sum, 0.0)
                        >= 0
                        else "sum_if_neg"
                    )
                    # >= instead of > is intended; usability decision: 0 is considered positive

                    formula_rslt_with_sign = [
                        (
                            grouping_key,
                            {**totals, sign_policy_with_value: totals["sum"]},
                        )
                        for grouping_key, totals in formula_rslt
                    ]

                    for sign_policy in ("sum_if_pos", "sum_if_neg"):
                        policy_expressions = expressions_by_sign_policy[sign_policy]

                        if policy_expressions:
                            if sign_policy == sign_policy_with_value:
                                rslt[formula, policy_expressions] = (
                                    _format_result_depending_on_groupby(
                                        formula_rslt_with_sign
                                    )
                                )
                            else:
                                rslt[formula, policy_expressions] = (
                                    _format_result_depending_on_groupby([])
                                )

                if expressions_by_sign_policy["no_sign_check"]:
                    rslt[formula, expressions_by_sign_policy["no_sign_check"]] = (
                        _format_result_depending_on_groupby(formula_rslt)
                    )

        _debug.pipeline(
            "domain_results",
            report=self,
            results=len(rslt),
            batch_ids_cached=len(batch_ids_cache)
            if batch_ids_cache is not None
            else None,
        )
        return rslt

    @_debug.perf.timed
    def _get_formula_batch_with_engine_account_codes(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        r"""Report engine.

        Formulas made for this engine target account prefixes. Each prefix used in the formula is evaluated as the sum of the move
        lines made on the accounts matching it. The formula syntax, whose elements can be freely combined
        (as in '123D\(1235) + 56 - 416C'), is:

        - 'PREFIX': sum of the balances of all accounts whose code starts with PREFIX.
        - '+' and '-': arithmetic operations between prefix results.
        - 'PREFIX\(SUB1,SUB2)': excludes the accounts starting with SUB1 or SUB2 from the ones matched by PREFIX.
        - 'PREFIXD' / 'PREFIXC': keeps the total balance of PREFIX only if it is positive (D, debit)
          respectively negative (C, credit); evaluates to 0 otherwise.
        - 'PREFIX\': empty exclusion, used to make a trailing C or D part of the prefix rather than a
          debit/credit match ('123D\' sums accounts starting with '123D', while '123D\C' keeps that sum only if negative).
        """
        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )
        prefilter = self.env["account.account"]._check_company_domain(
            self.get_report_company_ids(options)
        )

        all_accounts = (
            self.env["account.account"]
            .with_context(active_test=False)
            .search([*prefilter])
        )
        accounts = []

        for account in all_accounts:
            account_code = account.code
            if not account_code:
                for company in account.company_ids:
                    account_code = account.with_company(company).code
                    if account_code:
                        break
            accounts.append(
                {
                    "id": account.id,
                    "code": account_code,
                    "tag_ids": account.tag_ids.ids,
                }
            )

        accounts.sort(key=lambda acc: acc["code"])
        tags_map = defaultdict(list)
        for acc in accounts:
            # If an account has no tags, map it to the pseudo-tag `False` such
            # that a ref which does not exist matches it, otherwise DK balance
            # fails in `test_generate_all_export_files`
            for tag in acc["tag_ids"] or [False]:
                tags_map[tag].append(acc)

        accounts_prefix_map = defaultdict(set)
        # Gather the account code prefixes to compute the total from
        prefix_details_by_formula = {}  # in the form {formula: [(1, prefix1), (-1, prefix2)]}
        for formula in formulas_dict:
            prefix_details_by_formula[formula] = []
            for token in filter(
                None, ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(formula.replace(" ", ""))
            ):
                token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)

                if not token_match:
                    raise UserError(
                        _(
                            "Invalid token '%(token)s' in account_codes formula '%(formula)s'",
                            token=token,
                            formula=formula,
                        )
                    )

                multiplicator = -1 if token_match["sign"] == "-" else 1
                excluded_prefixes_match = token_match["excluded_prefixes"]
                excluded_prefixes = (
                    tuple(excluded_prefixes_match.split(","))
                    if excluded_prefixes_match
                    else ()
                )
                prefix = token_match["prefix"]

                # We group using both prefix and excluded_prefixes as keys, for the case where two expressions would
                # include the same prefix, but exlcude different prefixes (example 104\(1041) and 104\(1042))
                prefix_key = (prefix, *excluded_prefixes)
                prefix_details_by_formula[formula].append(
                    (multiplicator, prefix_key, token_match["balance_character"])
                )

                if tag := ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix):
                    if tag["ref"]:
                        tag_id = self.env["ir.model.data"]._xmlid_to_res_id(tag["ref"])
                    else:
                        tag_id = int(tag["id"])
                    accs = tags_map[tag_id]
                else:
                    idx = bisect.bisect_left(
                        accounts, prefix, key=lambda acc: acc["code"]
                    )
                    accs = itertools.takewhile(
                        lambda acc, prefix=prefix: acc["code"].startswith(prefix),
                        itertools.islice(accounts, idx, None),
                    )

                for account in accs:
                    if excluded_prefixes and account["code"].startswith(
                        excluded_prefixes
                    ):
                        continue
                    accounts_prefix_map[account["id"]].add(prefix_key)

        _debug.pipeline(
            "account_prefixes_mapped",
            report=self,
            date_scope=date_scope,
            groupby=current_groupby,
            formulas=len(prefix_details_by_formula),
            accounts=len(accounts),
            tags=len(tags_map),
            matched_accounts=len(accounts_prefix_map),
        )

        # Run main query
        query = self._get_report_query(options, date_scope)

        current_groupby_aml_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, query
            )
            if current_groupby
            else None
        )
        tail_query = self._get_engine_query_tail(offset, limit)
        if current_groupby_aml_sql and tail_query:
            tail_query_additional_groupby_where_sql = SQL(
                """
                AND %(current_groupby_aml_sql)s IN (
                    SELECT DISTINCT %(current_groupby_aml_sql)s
                    FROM %(table_references)s
                    WHERE %(search_condition)s
                    ORDER BY %(current_groupby_aml_sql)s
                    %(tail_query)s
                )
                """,
                current_groupby_aml_sql=current_groupby_aml_sql,
                # Must be the same FROM as the outer query: under budget reporting the
                # query shadows account_move_line with a budget-item subquery, and naming
                # the real table here would pick the load-more window from journal items
                # while the outer query aggregates budget rows.
                table_references=query.from_clause,
                search_condition=query.where_clause,
                tail_query=tail_query,
            )
        else:
            tail_query_additional_groupby_where_sql = SQL()
        _debug.logic(
            "account_codes_pagination",
            report=self,
            offset=offset,
            limit=limit,
            groupby_subquery=bool(tail_query_additional_groupby_where_sql),
        )

        extra_groupby_sql = (
            SQL(", %s", current_groupby_aml_sql) if current_groupby_aml_sql else SQL()
        )
        extra_select_sql = (
            SQL(", %s AS grouping_key", current_groupby_aml_sql)
            if current_groupby_aml_sql
            else SQL()
        )

        query = SQL(
            """
            SELECT
                account_move_line.account_id AS account_id,
                SUM(%(balance_select)s) AS sum
                %(extra_select_sql)s
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            %(tail_query_additional_groupby_where_sql)s
            GROUP BY account_move_line.account_id%(extra_groupby_sql)s
            %(order_by_sql)s
            %(tail_query)s
            """,
            extra_select_sql=extra_select_sql,
            table_references=query.from_clause,
            balance_select=self._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            currency_table_join=self._currency_table_aml_join(options),
            search_condition=query.where_clause,
            extra_groupby_sql=extra_groupby_sql,
            tail_query_additional_groupby_where_sql=tail_query_additional_groupby_where_sql,
            order_by_sql=SQL("ORDER BY %s", current_groupby_aml_sql)
            if current_groupby_aml_sql
            else SQL(),
            tail_query=tail_query
            if not tail_query_additional_groupby_where_sql
            else SQL(),
        )
        self.env.cr.execute(query)

        # Parse result
        rslt = {}

        res_by_prefix_account_id = {}
        for query_res in self.env.cr.dictfetchall():
            # Done this way so that we can run similar code for groupby and non-groupby
            grouping_key = query_res["grouping_key"] if current_groupby else None
            account_id = query_res["account_id"]
            for prefix_key in accounts_prefix_map[account_id]:
                res_by_prefix_account_id.setdefault(prefix_key, {}).setdefault(
                    account_id, []
                ).append(
                    (
                        grouping_key,
                        {
                            "result": query_res["sum"],
                            # A grouped row exists only where at least one line does,
                            # so its presence is the sublines flag.
                            "has_sublines": True,
                        },
                    )
                )
        _debug.perf.count("account_codes_rows_fetched", rows=self.env.cr.rowcount)
        _debug.pipeline(
            "account_codes_rows_parsed",
            report=self,
            prefixes_with_results=len(res_by_prefix_account_id),
        )

        for formula, prefix_details in prefix_details_by_formula.items():
            rslt_key = (formula, formulas_dict[formula])
            rslt_destination = rslt.setdefault(
                rslt_key,
                [] if current_groupby else {"result": 0, "has_sublines": False},
            )
            rslt_groups_by_grouping_keys = {}
            for multiplicator, prefix_key, balance_character in prefix_details:
                res_by_account_id = res_by_prefix_account_id.get(prefix_key, {})

                for account_results in res_by_account_id.values():
                    account_total_value = sum(
                        group_val["result"]
                        for (group_key, group_val) in account_results
                    )
                    comparator = self.env.company.currency_id.compare_amounts(
                        account_total_value, 0.0
                    )

                    # Manage balance_character.
                    if (
                        not balance_character
                        or (balance_character == "D" and comparator >= 0)
                        or (balance_character == "C" and comparator < 0)
                    ):
                        for group_key, group_val in account_results:
                            rslt_group = {
                                **group_val,
                                "result": multiplicator * group_val["result"],
                            }
                            if not current_groupby:
                                rslt_destination["result"] += rslt_group["result"]
                                rslt_destination["has_sublines"] = (
                                    rslt_destination["has_sublines"]
                                    or rslt_group["has_sublines"]
                                )
                            elif group_key in rslt_groups_by_grouping_keys:
                                # Will happen if the same grouping key is used on move lines with different accounts.
                                # This comes from the GROUPBY in the SQL query, which uses both grouping key and account.
                                # When this happens, we want to aggregate the results of each grouping key, to avoid duplicates in the end result.
                                already_treated_rslt_group = (
                                    rslt_groups_by_grouping_keys[group_key]
                                )
                                already_treated_rslt_group["has_sublines"] = (
                                    already_treated_rslt_group["has_sublines"]
                                    or rslt_group["has_sublines"]
                                )
                                already_treated_rslt_group["result"] += rslt_group[
                                    "result"
                                ]
                            else:
                                rslt_groups_by_grouping_keys[group_key] = rslt_group
                                rslt_destination.append((group_key, rslt_group))

        _debug.pipeline("account_codes_results", report=self, results=len(rslt))
        return rslt

    @_debug.perf.timed
    def _get_formula_batch_with_engine_external(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        """Report engine.

        This engine computes its result from the account.report.external.value objects that are linked to the expression.

        Two different formulas are possible:
        - sum: if the result must be the sum of all the external values in the period.
        - most_recent: it the result must be the value of the latest external value in the period, which can be a number or a text

        No subformula is allowed for this engine.
        """
        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )

        if current_groupby or next_groupby or offset or limit:
            raise UserError(
                _("'external' engine does not support groupby, limit nor offset.")
            )

        # Date clause
        date_from, date_to = self._get_date_bounds_info(options, date_scope)
        external_value_domain = [("date", "<=", date_to)]
        if date_from:
            external_value_domain.append(("date", ">=", date_from))
        _debug.logic(
            "external_date_bounds",
            report=self,
            date_scope=date_scope,
            date_from=date_from,
            date_to=date_to,
        )

        # Company clause
        external_value_domain.append(
            ("company_id", "in", self.get_report_company_ids(options))
        )

        # Do the computation
        where_clause = (
            self.env["account.report.external.value"]
            ._search(external_value_domain, bypass_access=True)
            .where_clause
        )

        # We have to execute two separate queries, one for text values and one for numeric values
        num_queries = []
        string_queries = []
        monetary_queries = []
        for formula, expressions in formulas_dict.items():
            query_end = SQL()
            if formula == "most_recent":
                query_end = SQL(
                    """
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                    """,
                )
            string_query = """
                    SELECT %(expression_id)s, text_value
                    FROM account_report_external_value
                    WHERE %(where_clause)s AND target_report_expression_id = %(expression_id)s
                    ORDER BY date DESC, id DESC
                    LIMIT 1
                """
            monetary_query = """
                SELECT
                    %(expression_id)s,
                    COALESCE(SUM(COALESCE(%(balance_select)s, 0)), 0)
                FROM account_report_external_value
                    %(currency_table_join)s
                WHERE %(where_clause)s AND target_report_expression_id = %(expression_id)s
                %(query_end)s
            """
            num_query = """
                    SELECT %(expression_id)s, SUM(COALESCE(value, 0))
                      FROM account_report_external_value
                     WHERE %(where_clause)s AND target_report_expression_id = %(expression_id)s
               %(query_end)s
            """

            for expression in expressions:
                if expression.figure_type == "string":
                    string_queries.append(
                        SQL(
                            string_query,
                            expression_id=expression.id,
                            where_clause=where_clause,
                        )
                    )
                elif expression.figure_type == "monetary":
                    monetary_queries.append(
                        SQL(
                            monetary_query,
                            expression_id=expression.id,
                            balance_select=self._currency_table_apply_rate(
                                SQL("CAST(value AS numeric)")
                            ),
                            currency_table_join=SQL(
                                """
                                JOIN %(currency_table)s
                                ON account_currency_table.company_id = account_report_external_value.company_id
                                AND account_currency_table.rate_type = 'current'
                            """,
                                currency_table=self._get_currency_table(options),
                            ),
                            where_clause=where_clause,
                            query_end=query_end,
                        )
                    )
                else:
                    num_queries.append(
                        SQL(
                            num_query,
                            expression_id=expression.id,
                            where_clause=where_clause,
                            query_end=query_end,
                        )
                    )

        _debug.pipeline(
            "external_queries_built",
            report=self,
            formulas=len(formulas_dict),
            numeric=len(num_queries),
            string=len(string_queries),
            monetary=len(monetary_queries),
        )
        # Convert to dict to have expression ids as keys
        query_results_dict = {}
        for query_list in (num_queries, string_queries, monetary_queries):
            if query_list:
                query_results = self.env.execute_query(
                    SQL(" UNION ALL ").join(SQL("(%s)", query) for query in query_list)
                )
                query_results_dict.update(dict(query_results))
        _debug.perf.count(
            "external_values_fetched", report=self, rows=len(query_results_dict)
        )

        # Build result dict
        rslt = {}
        for formula, expressions in formulas_dict.items():
            for expression in expressions:
                expression_value = query_results_dict.get(expression.id)
                # If expression_value is None, we have no previous value for this expression (set default at 0.0)
                expression_value = expression_value or (
                    "" if expression.figure_type == "string" else 0.0
                )
                rslt[(formula, expression)] = {
                    "result": expression_value,
                    "has_sublines": False,
                }

        return rslt

    @_debug.perf.timed
    def _get_formula_batch_with_engine_custom(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )

        rslt = {}
        for formula, expressions in formulas_dict.items():
            custom_engine_function = self._get_custom_report_function(
                formula, "custom_engine"
            )
            rslt[(formula, expressions)] = custom_engine_function(
                expressions,
                options,
                date_scope,
                current_groupby,
                next_groupby,
                offset=offset,
                limit=limit,
                warnings=warnings,
            )
        _debug.pipeline(
            "custom_engine_results",
            report=self,
            date_scope=date_scope,
            groupby=current_groupby,
            formulas=len(formulas_dict),
            results=len(rslt),
        )
        return rslt

    @_debug.perf.timed
    def _get_domain_expression_audit_aml(self, expression_to_audit, options):
        """Returns the domain used to audit a single provided expression.

        'account_codes' engine's D and C formulas can't be handled by a domain: we make the choice to display
        everything for them (so, audit shows all the lines that are considered by the formula). To avoid confusion from the user
        when auditing such lines, a default group by account can be used in the list view.
        """
        _debug.logic(
            "audit_domain_engine",
            report=self,
            expression=expression_to_audit,
            engine=expression_to_audit.engine,
            supported=expression_to_audit.engine
            in ("account_codes", "tax_tags", "domain"),
        )
        if expression_to_audit.engine == "account_codes":
            formula = expression_to_audit.formula.replace(" ", "")

            account_codes_domains = []
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(
                formula.replace(" ", "")
            ):
                if token:
                    match_dict = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(
                        token
                    ).groupdict()
                    tag_match = ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(
                        match_dict["prefix"]
                    )
                    account_codes_domain = []

                    if tag_match:
                        if tag_match["ref"]:
                            tag_id = self.env["ir.model.data"]._xmlid_to_res_id(
                                tag_match["ref"]
                            )
                        else:
                            tag_id = int(tag_match["id"])

                        account_codes_domain.append(
                            ("account_id.tag_ids", "in", [tag_id])
                        )
                    else:
                        account_codes_domain.append(
                            ("account_id.code", "=like", f"{match_dict['prefix']}%")
                        )

                    excluded_prefix_str = match_dict["excluded_prefixes"]
                    if excluded_prefix_str:
                        for excluded_prefix in excluded_prefix_str.split(","):
                            # "'not like', prefix%" doesn't work
                            account_codes_domain += [
                                "!",
                                ("account_id.code", "=like", f"{excluded_prefix}%"),
                            ]

                    account_codes_domains.append(account_codes_domain)

            _debug.pipeline(
                "account_codes_audit_domain",
                expression=expression_to_audit,
                tokens=len(account_codes_domains),
            )
            return Domain.OR(account_codes_domains)

        if expression_to_audit.engine == "tax_tags":
            tags = self.env["account.account.tag"]._get_tax_tags(
                expression_to_audit.formula,
                expression_to_audit.report_line_id.report_id.country_id.id,
            )
            return [("tax_tag_ids", "in", tags.ids)]

        if expression_to_audit.engine == "domain":
            return literal_eval(expression_to_audit.formula)

        return None

    @api.model
    def _currency_table_apply_rate(self, value: SQL) -> SQL:
        """Returns an SQL term to use in a SELECT statement converting the value passed as parameter into the current company's currency, using the
        currency table (which must be joined in the query as well ; using _currency_table_aml_join for account.move.line, or _get_currency_table for
        other more specific uses).
        """
        return SQL(
            "(%(value)s) * COALESCE(account_currency_table.rate, 1)", value=value
        )

    @api.model
    @_debug.perf.timed
    def _currency_table_aml_join(
        self,
        options,
        aml_alias=SQL("account_move_line"),  # noqa: B008  SQL is immutable, one shared default is safe
    ) -> SQL:
        """Returns the JOIN condition to the currency table in a query needing to use it to convert aml balances from one currency to another."""
        _debug.logic(
            "currency_table_join",
            table_type=options.get("currency_table", {}).get("type"),
            period_key=options.get("date", {}).get("currency_table_period_key"),
        )
        if options["currency_table"]["type"] == "cta":
            return SQL(
                """
                    JOIN account_account aml_ct_account
                        ON aml_ct_account.id = %(aml_table)s.account_id
                    LEFT JOIN %(currency_table)s
                        ON %(aml_table)s.company_id = account_currency_table.company_id
                        AND (
                            account_currency_table.rate_type = CASE
                                WHEN aml_ct_account.account_type LIKE ANY (ARRAY[%(income_prefix)s, %(expense_prefix)s, 'equity_unaffected']) THEN 'average'
                                WHEN aml_ct_account.account_type LIKE %(equity_prefix)s THEN 'historical'
                                ELSE 'current'
                            END
                        )
                        AND (account_currency_table.date_from IS NULL OR account_currency_table.date_from <= %(aml_table)s.date)
                        AND (account_currency_table.date_next IS NULL OR account_currency_table.date_next > %(aml_table)s.date)
                        AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
                """,
                aml_table=aml_alias,
                equity_prefix="equity%",
                income_prefix="income%",
                expense_prefix="expense%",
                currency_table=self._get_currency_table(options),
                period_key=options["date"]["currency_table_period_key"],
            )

        return SQL(
            """
                JOIN %(currency_table)s
                    ON %(aml_table)s.company_id = account_currency_table.company_id
                    AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
            """,
            aml_table=aml_alias,
            currency_table=self._get_currency_table(options),
            period_key=options["date"]["currency_table_period_key"],
        )

    @api.model
    def _get_currency_table(self, options) -> SQL:
        """Returns the currency table table definition to be injected in the JOIN condition of an SQL query needing to use it."""
        if options["currency_table"]["type"] == "monocurrency":
            companies = self.env["res.company"].browse(
                self.get_report_company_ids(options)
            )
            # No CTA rates here by construction: this branch is the monocurrency one.
            return self.env["res.currency"]._get_monocurrency_currency_table_sql(
                companies, use_cta_rates=False
            )

        return SQL("account_currency_table")

    @_debug.perf.timed
    def _get_report_query(self, options, date_scope, domain=None) -> Query:
        """Get a Query object that references the records needed for this report."""
        _debug.logic(
            "report_query_scope",
            report=self,
            date_scope=date_scope,
            extra_domain=domain is not None,
            budget=options.get("compute_budget"),
        )
        domain = self._get_domain_options(options, date_scope) & Domain(
            domain or Domain.TRUE
        )

        if options.get("compute_budget"):
            # remove required columns that are not filled from the domain
            # these are not in the budget table
            domain = domain.optimize(self.env["account.move.line"])
            aml_required_columns = {
                "move_id",
                "currency_id",
                "journal_id",
                "display_type",
            }
            domain = domain.map_conditions(
                lambda condition: (
                    Domain.TRUE
                    if condition.field_expr in aml_required_columns
                    else condition
                )
            )

        query = self.env["account.move.line"]._search(domain)

        if options.get("compute_budget"):
            query._tables["account_move_line"] = (
                self._create_aml_shadowing_query_for_budget(options)
            )
            # add_where appends to the query's where clauses, which are already ANDed
            # together; passing query.where_clause back in would emit the whole domain twice.
            query.add_where(SQL("budget_id = %s", options["compute_budget"]))

        return query

    def _get_engine_query_tail(self, offset, limit) -> SQL:
        """Helper to generate the OFFSET, LIMIT and ORDER conditions of formula engines' queries."""
        query_tail = SQL()

        if offset:
            query_tail = SQL("%s OFFSET %s", query_tail, offset)

        if limit:
            query_tail = SQL("%s LIMIT %s", query_tail, limit)

        return query_tail

    def _get_batch_model_ids(self, batch_model, domain, batch_ids_cache=None):
        """Resolve a batched domain to the ids of the comodel records it selects.

        The domain comes from the expression's formula alone, so the answer is the same
        for every column group of a render; batch_ids_cache, when the caller provides
        one, holds it for the duration of that render.
        """
        if not batch_model:
            return [None]

        cache_key = (batch_model, repr(domain))
        if batch_ids_cache is not None and cache_key in batch_ids_cache:
            _debug.perf.count(
                "batch_ids_cache_hit",
                rows=len(batch_ids_cache[cache_key]),
                batch_model=batch_model,
            )
            return batch_ids_cache[cache_key]

        ids = self.env[batch_model].with_context(active_test=False).search(domain).ids
        _debug.perf.count(
            "batch_ids_searched",
            rows=len(ids),
            batch_model=batch_model,
            cached=batch_ids_cache is not None,
        )
        if batch_ids_cache is not None:
            batch_ids_cache[cache_key] = ids
        return ids

    @api.model
    def _is_id_positive_condition(self, operator, value):
        """Whether (many2one_field, operator, value) keeps its meaning when rewritten as a
        condition on the comodel's id, as the domain engine's batching does.
        """
        if operator == "=":
            return isinstance(value, int) and not isinstance(value, bool)
        if operator == "in":
            return isinstance(value, (list, tuple, set)) and all(
                isinstance(v, int) and not isinstance(v, bool) for v in value
            )
        return False

    @_debug.perf.timed
    def _check_groupby_fields(self, groupby_fields_name: list[str] | str):
        """Checks that each string in the groupby_fields_name list is a valid groupby value for an accounting report.
        So it must be:
        - a field from account.move.line which is (1) searchable and (2) for which _field_to_sql is implemented,
          this includes stored and related non-stored fields, or
        - a custom value allowed by the _get_custom_groupby_map function of the custom handler
        """
        self.check_singleton()
        if isinstance(groupby_fields_name, str | bool):
            groupby_fields_name = (
                groupby_fields_name.split(",") if groupby_fields_name else []
            )

        custom_handler_name = self._get_custom_handler_model()
        _debug.logic(
            "groupby_fields_checking",
            report=self,
            fields=groupby_fields_name,
            custom_handler=custom_handler_name,
        )

        for field_name in (fname.strip() for fname in groupby_fields_name):
            groupby_field = self.env["account.move.line"]._fields.get(field_name)
            if groupby_field:
                if not groupby_field._description_searchable:
                    raise UserError(
                        self.env._(
                            "Field %s of account.move.line is not searchable and can therefore not be used in a groupby expression.",
                            field_name,
                        )
                    )
                try:
                    self.env["account.move.line"]._field_to_sql(
                        "account_move_line",
                        field_name,
                        Query(self.env, "account_move_line"),
                    )
                except ValueError:
                    raise UserError(
                        self.env._(
                            "Field %s of account.move.line cannot be used in a groupby expression.",
                            field_name,
                        )
                    ) from None
            elif custom_handler_name:
                if (
                    field_name
                    not in self.env[custom_handler_name]._get_custom_groupby_map()
                ):
                    raise UserError(
                        _(
                            "Field %s does not exist on account.move.line, and is not supported by this report's custom handler.",
                            field_name,
                        )
                    )
            else:
                raise UserError(
                    _("Field %s does not exist on account.move.line.", field_name)
                )
