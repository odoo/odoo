import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from .account_report import (
    DOMAIN_REGEX,
    REFERENCE_UNSAFE_CHARS_REGEX,
)

_debug = DebugLog(__name__)


def _replace_codes_in_formula(formula, code_mapping):
    if not code_mapping:
        return formula
    alternatives = "|".join(
        re.escape(old_code) for old_code in sorted(code_mapping, key=len, reverse=True)
    )
    return re.sub(
        rf"(?<=\W)(?:{alternatives})(?=\W)",
        lambda match: code_mapping[match.group()],
        f" {formula} ",
    ).strip()


class AccountReportLine(models.Model):
    _name = "report.formula.line"
    _description = "Formula Report Line"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    expression_ids = fields.One2many(
        comodel_name="report.formula.expression",
        inverse_name="report_line_id",
        string="Expressions",
    )
    report_id = fields.Many2one(
        comodel_name="report.formula",
        string="Parent Report",
        compute="_compute_report_id",
        precompute=True,
        recursive=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        ondelete="cascade",
    )
    hierarchy_level = fields.Integer(
        string="Level",
        compute="_compute_hierarchy_level",
        precompute=True,
        recursive=True,
        store=True,
        readonly=False,
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name="report.formula.line",
        string="Parent Line",
        index="btree_not_null",
        ondelete="set null",
    )
    children_ids = fields.One2many(
        comodel_name="report.formula.line",
        inverse_name="parent_id",
        string="Child Lines",
    )
    groupby = fields.Char(
        string="Group By",
        help="Comma-separated list of fields from account.move.line (Journal Item). When set, this line will generate sublines grouped by those keys.",
    )
    user_groupby = fields.Char(
        string="User Group By",
        compute="_compute_user_groupby",
        precompute=True,
        store=True,
        readonly=False,
        help="Comma-separated list of fields from account.move.line (Journal Item). When set, this line will generate sublines grouped by those keys.",
    )
    sequence = fields.Integer()
    code = fields.Char(help="Unique identifier for this line.")
    foldable = fields.Boolean(
        help="By default, we always unfold the lines that can be. If this is checked, the line won't be unfolded by default, and a folding button will be displayed."
    )
    print_on_new_page = fields.Boolean(
        help="When checked this line and everything after it will be printed on a new page."
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        help="Setting this field will turn the line into a link, executing the action when clicked.",
    )
    hide_if_zero = fields.Boolean(
        string="Hide if Zero",
        help="This line and its children will be hidden when all of their columns are 0.",
    )
    domain_formula = fields.Char(
        string="Domain Formula Shortcut",
        inverse="_inverse_domain_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the domain engine",
    )
    aggregation_formula = fields.Char(
        string="Aggregation Formula Shortcut",
        inverse="_inverse_aggregation_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the aggregation engine",
    )
    external_formula = fields.Char(
        string="External Formula Shortcut",
        inverse="_inverse_external_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the external engine",
    )
    horizontal_split_side = fields.Selection(
        selection=[("left", "Left"), ("right", "Right")],
        compute="_compute_horizontal_split_side",
        recursive=True,
        store=True,
        readonly=False,
    )

    display_custom_groupby_warning = fields.Boolean(
        compute="_compute_display_custom_groupby_warning"
    )

    _code_uniq = models.UniqueIndex(
        "(report_id, code) WHERE code IS NOT NULL",
        "A report line with the same code already exists.",
    )

    @api.constrains("code")
    @_debug.perf.timed
    def _check_code(self):
        for report_line in self:
            if report_line.code and REFERENCE_UNSAFE_CHARS_REGEX.search(
                report_line.code
            ):
                raise ValidationError(
                    self.env._(
                        'The code of line "%(line)s" is "%(code)s". A code is what an '
                        "aggregation formula and a carryover target name a line by, so "
                        "it cannot contain a dot, a bracket, whitespace or an operator.",
                        line=report_line.name,
                        code=report_line.code,
                    )
                )

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for report_line in self:
            if report_line.parent_id:
                increase_level = 3 if report_line.parent_id.hierarchy_level == 0 else 2
                report_line.hierarchy_level = (
                    report_line.parent_id.hierarchy_level + increase_level
                )
            else:
                report_line.hierarchy_level = 1

    @api.depends("parent_id.report_id")
    def _compute_report_id(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.report_id = report_line.parent_id.report_id

    @api.depends("parent_id.horizontal_split_side")
    def _compute_horizontal_split_side(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.horizontal_split_side = (
                    report_line.parent_id.horizontal_split_side
                )

    def _compute_user_groupby(self):
        for report_line in self:
            report_line.user_groupby = report_line.groupby

    @api.constrains("parent_id")
    @_debug.perf.timed
    def _check_groupby_no_child(self):
        for report_line in self:
            if report_line.parent_id.groupby or report_line.parent_id.user_groupby:
                raise ValidationError(
                    self.env._(
                        "A line cannot have both children and a groupby value (line '%s').",
                        report_line.parent_id.name,
                    )
                )

    @api.constrains("parent_id", "report_id")
    @_debug.perf.timed
    def _check_parent_report(self):
        for line in self:
            if line.parent_id and line.parent_id.report_id != line.report_id:
                raise ValidationError(
                    self.env._(
                        'Line "%(line)s" belongs to report "%(report)s" but its parent '
                        '"%(parent)s" belongs to "%(parent_report)s". A line and its '
                        "parent must be in the same report.",
                        line=line.name,
                        report=line.report_id.display_name,
                        parent=line.parent_id.name,
                        parent_report=line.parent_id.report_id.display_name,
                    )
                )

    @api.constrains("parent_id")
    @_debug.perf.timed
    def _check_parent_line(self):
        for line in self.filtered(lambda x: x.parent_id == x):
            raise ValidationError(
                self.env._('Line "%s" defines itself as its parent.', line.name)
            )
        if self._has_cycle("parent_id"):
            raise ValidationError(
                self.env._("Report lines cannot form a recursive parent hierarchy.")
            )

    @_debug.perf.timed
    def _copy_hierarchy(self, copied_report):
        line_ids = set(self.ids)
        lines_by_parent_id = defaultdict(self.browse)
        for line in self:
            parent_id = line.parent_id.id if line.parent_id.id in line_ids else False
            lines_by_parent_id[parent_id] |= line

        code_mapping = {}
        taken_codes = set()

        def allocate_codes(line):
            if line.code:
                code = f"{line.code}_COPY"
                while code in taken_codes:
                    code = f"{code}_COPY"
                taken_codes.add(code)
                code_mapping[line.code] = code
            for child in lines_by_parent_id[line.id]:
                allocate_codes(child)

        for root in lines_by_parent_id[False]:
            allocate_codes(root)
        _debug.pipeline(
            "hierarchy_codes_allocated",
            report=copied_report,
            lines=self,
            roots=len(lines_by_parent_id[False]),
            renamed_codes=len(code_mapping),
        )

        copied_line_by_id = {}
        generation = lines_by_parent_id[False]
        while generation:
            vals_list = generation.copy_data()
            for line, vals in zip(generation, vals_list, strict=True):
                vals["report_id"] = copied_report.id
                vals["parent_id"] = (
                    copied_line_by_id[line.parent_id.id].id
                    if line.parent_id.id in copied_line_by_id
                    else False
                )
                vals["code"] = code_mapping.get(line.code, False)
            for line, copied_line in zip(
                generation, self.create(vals_list), strict=True
            ):
                copied_line_by_id[line.id] = copied_line
            next_generation = self.browse()
            for line in generation:
                next_generation |= lines_by_parent_id[line.id]
            _debug.pipeline(
                "hierarchy_generation_copied",
                report=copied_report,
                copied=len(vals_list),
                next_generation=len(next_generation),
            )
            generation = next_generation

        source_expressions = self.expression_ids
        if source_expressions:
            vals_list = source_expressions.copy_data()
            for expression, vals in zip(source_expressions, vals_list, strict=True):
                vals["report_line_id"] = copied_line_by_id[
                    expression.report_line_id.id
                ].id
                if expression.engine == "aggregation":
                    for key in ("formula", "subformula"):
                        if vals.get(key):
                            vals[key] = _replace_codes_in_formula(
                                vals[key], code_mapping
                            )
            _debug.pipeline(
                "hierarchy_expressions_copied",
                report=copied_report,
                expressions=source_expressions,
                copied_lines=len(copied_line_by_id),
            )
            self.env["report.formula.expression"].create(vals_list)

        return code_mapping

    def _inverse_domain_formula(self):
        self._create_report_expression(engine="domain")

    def _inverse_aggregation_formula(self):
        self._create_report_expression(engine="aggregation")

    def _inverse_external_formula(self):
        self._create_report_expression(engine="external")

    def _get_shortcut_expression_formula(self, engine):
        self.check_singleton()
        if engine == "domain" and self.domain_formula:
            domain_match = DOMAIN_REGEX.match(self.domain_formula)
            if not domain_match:
                raise ValidationError(
                    self.env._(
                        "Invalid domain formula '%(formula)s' on report line "
                        "'%(line)s'. Expected the form 'sum(<domain>)' "
                        "(optionally '-sum(<domain>)').",
                        formula=self.domain_formula,
                        line=self.name,
                    )
                )
            subformula, formula = domain_match.groups()
            formula = re.sub(
                r"""\bref\((?P<quote>['"])(?P<xmlid>.+?)(?P=quote)\)""",
                lambda m: str(self.env.ref(m["xmlid"]).id),
                formula,
            )
            return subformula, formula
        if engine == "aggregation" and self.aggregation_formula:
            return None, self.aggregation_formula
        if engine == "external" and self.external_formula:
            if self.external_formula == "percentage":
                return "editable;rounding=0", "most_recent"
            if self.external_formula == "monetary":
                return "editable", "sum"
            return "editable", "most_recent"
        return None

    @_debug.perf.timed
    def _create_report_expression(self, engine):
        vals_list = []
        xml_ids = self.expression_ids.filtered(
            lambda exp: exp.label == "balance"
        ).get_external_id()
        for report_line in self:
            shortcut = report_line._get_shortcut_expression_formula(engine)
            if shortcut:
                subformula, formula = shortcut
            else:
                report_line.expression_ids.filtered(
                    lambda exp: (
                        exp.engine == engine
                        and exp.label == "balance"
                        and not xml_ids.get(exp.id)
                    )
                ).unlink()
                continue

            vals = {
                "report_line_id": report_line.id,
                "label": "balance",
                "engine": engine,
                "formula": formula,
                "subformula": subformula,
                "figure_type": (
                    report_line.external_formula if engine == "external" else False
                ),
            }

            balance_expression = report_line.expression_ids.filtered(
                lambda exp: exp.label == "balance"
            )
            if not balance_expression:
                vals_list.append(vals)
            elif xml_ids.get(balance_expression.id):
                balance_expression.unlink()
                vals_list.append(vals)
            else:
                balance_expression.write(vals)

        _debug.pipeline(
            "report_expressions_synced",
            engine=engine,
            lines=self,
            created=len(vals_list),
        )
        if vals_list:
            self.env["report.formula.expression"].create(vals_list)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_child_expressions(self):
        _debug.lifecycle("_unlink_child_expressions", records=self)
        self.expression_ids.unlink()

    @api.depends("groupby", "user_groupby")
    def _compute_display_custom_groupby_warning(self):
        for line in self:
            line.display_custom_groupby_warning = (
                line.get_external_id()[line.id] and line.user_groupby != line.groupby
            )

    @api.constrains("groupby", "user_groupby")
    @_debug.perf.timed
    def _check_groupby(self):
        self.expression_ids._check_engine()
        for report_line in self:
            report_line.report_id._check_groupby_fields(report_line.user_groupby)
            report_line.report_id._check_groupby_fields(report_line.groupby)

    @_debug.perf.timed
    def _expand_groupby(
        self,
        line_dict_id,
        groupby,
        options,
        offset=0,
        limit=None,
        load_one_more=False,
        unfold_all_batch_data=None,
    ):
        """Expand function used to get the sublines of a groupby.
        groupby param is a string consisting of one or more coma-separated field names. Only the first one
        will be used for the expansion; if there are subsequent ones, the generated lines will themselves used them as
        their groupby value, and point to this expand_function, hence generating a hierarchy of groupby).
        """
        self.check_singleton()

        group_indent = 0
        line_id_list = self.report_id._parse_line_id(line_dict_id)

        # Parse groupby
        groupby_data = self._parse_groupby(options, groupby_to_expand=groupby)
        groupby_model = groupby_data["current_groupby_model"]
        next_groupby = groupby_data["next_groupby"]
        current_groupby = groupby_data["current_groupby"]
        custom_groupby_map = groupby_data["custom_groupby_map"]

        # If this line is a sub-groupby of groupby line (for example, when grouping by partner, id; the id line is a subgroup of partner),
        # we need to add the domain of the parent groupby criteria to the options
        prefix_groups_count = 0
        sub_groupby_domain = []
        full_sub_groupby_key_elements = []
        parent_groupby_nber = 0
        for markup, model, value in line_id_list:
            if isinstance(markup, dict) and "groupby" in markup:
                parent_groupby_nber += 1
                field_name = markup["groupby"]
                if field_name in custom_groupby_map:
                    sub_groupby_domain += custom_groupby_map[field_name][
                        "domain_builder"
                    ](value)
                else:
                    sub_groupby_domain.append((field_name, "=", value))
                full_sub_groupby_key_elements.append(f"{field_name}:{value}")
            elif isinstance(markup, dict) and "groupby_prefix_group" in markup:
                prefix_groups_count += 1

            if model in self._get_indenting_groupby_models():
                group_indent += 1

        if sub_groupby_domain:
            forced_domain = options.get("forced_domain", []) + sub_groupby_domain
            options = {**options, "forced_domain": forced_domain}
        _debug.logic(
            "groupby_parsed",
            report=self.report_id,
            report_line=self,
            line_dict_id=line_dict_id,
            current_groupby=current_groupby,
            next_groupby=next_groupby,
            groupby_model=groupby_model,
            parent_groupbys=parent_groupby_nber,
            prefix_groups=prefix_groups_count,
            sub_groupby_domain_len=len(sub_groupby_domain),
        )

        # If the report transmitted custom_unfold_all_batch_data dictionary, use it
        full_sub_groupby_key = (
            f"[{self.id}]{','.join(full_sub_groupby_key_elements)}=>{current_groupby}"
        )

        cached_result = (unfold_all_batch_data or {}).get(full_sub_groupby_key)

        if cached_result is not None or options.get("test_unfold_all"):
            all_column_groups_expression_totals = cached_result
        else:
            all_column_groups_expression_totals = (
                self.report_id._compute_expression_totals_for_each_column_group(
                    self.expression_ids,
                    options,
                    groupby_to_expand=groupby,
                    offset=offset,
                    limit=limit + 1 if limit and load_one_more else limit,
                )
            )
        _debug.logic(
            "groupby_totals_source",
            report_line=self,
            source="unfold_all_batch"
            if cached_result is not None
            else ("test_unfold_all" if options.get("test_unfold_all") else "computed"),
            offset=offset,
            limit=limit,
            load_one_more=load_one_more,
        )

        # Put similar grouping keys from different totals/periods together, so that we don't display multiple
        # lines for the same grouping key

        figure_types_defaulting_to_0 = {"monetary", "percentage", "integer", "float"}

        default_value_per_expr_label = {
            col_opt["expression_label"]: 0
            if col_opt["figure_type"] in figure_types_defaulting_to_0
            else None
            for col_opt in options["columns"]
        }

        # Gather default value for each expression, in case it has no value for a given grouping key
        default_value_per_expression = {}
        for expression in self.expression_ids:
            if expression.figure_type:
                default_value = (
                    0
                    if expression.figure_type in figure_types_defaulting_to_0
                    else None
                )
            else:
                default_value = default_value_per_expr_label.get(expression.label)

            default_value_per_expression[expression] = {"value": default_value}

        # Build each group's result
        aggregated_group_totals = defaultdict(
            lambda: defaultdict(default_value_per_expression.copy)
        )
        for (
            column_group_key,
            expression_totals,
        ) in all_column_groups_expression_totals.items():
            for expression in self.expression_ids:
                sublines_info = expression_totals[expression]["sublines_info"]
                for grouping_key, result in expression_totals[expression]["value"]:
                    aggregated_group_totals[grouping_key][column_group_key][
                        expression
                    ] = {
                        "value": result,
                        "sublines_info": grouping_key in sublines_info,
                    }

        # Generate groupby lines
        group_lines_by_keys = {}
        for grouping_key, group_totals in aggregated_group_totals.items():
            # For this, we emulate a dict formatted like the result of _compute_expression_totals_for_each_column_group, so that we can call
            # _prepare_static_line_columns like on non-grouped lines
            line_id = self.report_id._get_generic_line_id(
                groupby_model,
                grouping_key,
                parent_line_id=line_dict_id,
                markup={"groupby": current_groupby},
            )
            caret_option = None
            if not next_groupby:
                caret_builder = custom_groupby_map.get(current_groupby, {}).get(
                    "caret_builder", {}
                )
                if caret_builder:
                    caret_option = caret_builder(grouping_key)
                else:
                    caret_option = groupby_model

            columns = self.report_id._prepare_static_line_columns(
                self, options, group_totals, groupby_model=groupby_model
            )
            has_children = bool(next_groupby) and any(
                col["has_sublines"] for col in columns
            )

            group_line_dict = {
                # 'name' key will be set later, so that we can browse all the records of this expansion at once (in case we're dealing with records)
                "id": line_id,
                "unfoldable": has_children,
                "unfolded": (has_children and next_groupby and options["unfold_all"])
                or line_id in options["unfolded_lines"],
                "groupby": next_groupby,
                "columns": columns,
                "level": self.hierarchy_level
                + 2 * (prefix_groups_count + parent_groupby_nber + 1)
                + (group_indent - 1),
                "parent_id": line_dict_id,
                "expand_function": "_report_expand_unfoldable_line_with_groupby"
                if next_groupby
                else None,
                "caret_options": caret_option,
            }

            if self.report_id.custom_handler_model_id:
                self.env[
                    self.report_id.custom_handler_model_name
                ]._custom_groupby_line_completer(
                    self.report_id, options, group_line_dict, current_groupby
                )

            # Growth comparison column.
            if options.get("column_percent_comparison") == "growth":
                compared_expression = self.expression_ids.filtered(
                    lambda expr, group_line_dict=group_line_dict: (
                        expr.label == group_line_dict["columns"][0]["expression_label"]
                    )
                )

                if options["comparison"]["period_order"] == "descending":
                    first_value, second_value = (
                        group_line_dict["columns"][0]["no_format"],
                        group_line_dict["columns"][1]["no_format"],
                    )
                else:
                    first_value, second_value = (
                        group_line_dict["columns"][1]["no_format"],
                        group_line_dict["columns"][0]["no_format"],
                    )

                group_line_dict["column_percent_comparison_data"] = (
                    self.report_id._get_column_percent_comparison_data(
                        options,
                        first_value,
                        second_value,
                        green_on_positive=compared_expression.green_on_positive,
                    )
                )
            # Manage budget comparison
            elif options.get("column_percent_comparison") == "budget":
                self.report_id._set_budget_column_comparisons(options, group_line_dict)
            elif options.get("column_percent_comparison") == "analytic_coverage":
                group_line_dict["column_percent_comparison_data"] = (
                    self.report_id._get_column_percent_comparison_data(
                        options,
                        group_line_dict["columns"][0]["no_format"],
                        group_line_dict["columns"][1]["no_format"],
                        green_on_positive=False,
                    )
                )
            group_lines_by_keys[grouping_key] = group_line_dict

        _debug.pipeline(
            "groupby_lines_built",
            report_line=self,
            groups=len(group_lines_by_keys),
            column_groups=len(all_column_groups_expression_totals),
            percent_comparison=options.get("column_percent_comparison"),
        )
        draft_entries = {}  # move state used order to color the line if it's draft
        # Sort grouping keys in the right order and generate line names
        keys_and_names_in_sequence = {}  # Order of this dict will matter

        custom_groupby_name_builder = custom_groupby_map.get(current_groupby, {}).get(
            "label_builder"
        )
        if groupby_model and not custom_groupby_name_builder:
            browsed_groupby_keys = self.env[groupby_model].browse(
                [key for key in group_lines_by_keys if key is not None]
            )

            out_of_sorting_record = None
            records_to_sort = browsed_groupby_keys
            if (
                browsed_groupby_keys
                and load_one_more
                and len(browsed_groupby_keys) >= limit
            ):
                out_of_sorting_record = browsed_groupby_keys[-1]
                records_to_sort = records_to_sort[:-1]

            for record in records_to_sort.with_context(active_test=False).sorted():
                keys_and_names_in_sequence[record.id] = record.display_name

                draft_entries[record.id] = self._get_groupby_record_state(
                    groupby_model, record
                )

            if None in group_lines_by_keys:
                keys_and_names_in_sequence[None] = self.env._("Unknown")

            if out_of_sorting_record:
                keys_and_names_in_sequence[out_of_sorting_record.id] = (
                    out_of_sorting_record.display_name
                )

        elif custom_groupby_name_builder:
            keys_and_names_in_sequence = custom_groupby_name_builder(
                group_lines_by_keys.keys()
            )  # Batch this when we have a label builder. This function also ensures the order of the name sequence
        else:
            for non_relational_key in sorted(
                group_lines_by_keys.keys(),
                key=lambda k: (k is None, isinstance(k, str), k),
            ):
                if non_relational_key is None:
                    keys_and_names_in_sequence[non_relational_key] = self.env._(
                        "Undefined"
                    )
                else:
                    groupby_field = self.report_id._get_required_source_model()._fields[
                        groupby_data["current_groupby"]
                    ]
                    if groupby_field.type == "selection":
                        selection_options = dict(
                            groupby_field._description_selection(self.env)
                        )
                        keys_and_names_in_sequence[non_relational_key] = (
                            selection_options.get(non_relational_key)
                            or self.env._("Undefined")
                        )
                    else:
                        keys_and_names_in_sequence[non_relational_key] = str(
                            non_relational_key
                        )
        _debug.logic(
            "group_names_strategy",
            report_line=self,
            strategy="label_builder"
            if custom_groupby_name_builder
            else ("records" if groupby_model else "raw_values"),
            named=len(keys_and_names_in_sequence),
        )

        # Build result: add a name to the groupby lines and handle totals below section for multi-level groupby
        group_lines = []
        for grouping_key, line_name in keys_and_names_in_sequence.items():
            group_line_dict = group_lines_by_keys[grouping_key]
            group_line_dict["name"] = line_name
            if draft_entries.get(grouping_key) == "draft":
                group_line_dict["is_draft"] = True
            group_lines.append(group_line_dict)

        if options.get("hierarchy"):
            group_lines = self.report_id._create_hierarchy(group_lines, options)

        _debug.pipeline(
            "groupby_expanded",
            report_line=self,
            group_lines=len(group_lines),
            drafts=len(draft_entries),
            hierarchy=bool(options.get("hierarchy")),
        )
        return group_lines

    @_debug.perf.timed
    def _parse_groupby(self, options, groupby_to_expand=None):
        """Retrieves the information needed to handle the groupby feature on the current line.

        :param groupby_to_expand:    A coma-separated string containing, in order, all the fields that are used in the groupby we're expanding.
                                     None if we're not expanding anything.

        :return: A dictionary with 4 keys:
            'current_groupby':       The name of the value to be used to retrieve the results of the current groupby we're
                                     expanding, or None if nothing is being expanded. That value can be either a field of account.move.line, or
                                     a custom groupby value defined in this report's custom handler's _get_custom_groupby_map function.

            'next_groupby':          The subsequent groupings to be applied after current_groupby, as a string of coma-separated values (again,
                                     either field names from account.move.line or a custom groupby defined on the handler).
                                     If no subsequent grouping exists, next_groupby will be None.

            'current_groupby_model': The model name corresponding to current_groupby, or None if current_groupby is None.

            'custom_groupby_map';    The groupby map, used to handle custom groupby values, as returned by the _get_custom_groupby_map function
                                     of the custom handler (by default, it will be an empty dict)

        Each expansion consumes the leftmost field of groupby_to_expand into current_groupby and
        leaves the remainder in next_groupby, which becomes the groupby_to_expand of the next level.
        """
        self.check_singleton()

        if groupby_to_expand:
            groupby_to_expand = groupby_to_expand.replace(" ", "")
            split_groupby = groupby_to_expand.split(",")
            current_groupby = split_groupby[0]
            next_groupby = (
                ",".join(split_groupby[1:]) if len(split_groupby) > 1 else None
            )
        else:
            current_groupby = None
            groupby = self._get_groupby(options)
            next_groupby = groupby.replace(" ", "") if groupby else None

        custom_handler_name = self.report_id._get_custom_handler_model()
        custom_groupby_map = (
            self.env[custom_handler_name]._get_custom_groupby_map()
            if custom_handler_name
            else {}
        )
        if current_groupby in custom_groupby_map:
            groupby_model = custom_groupby_map[current_groupby]["model"]
        elif current_groupby == "id":
            groupby_model = self.report_id._get_required_source_model()._name
        elif current_groupby:
            groupby_model = (
                self.report_id._get_required_source_model()
                ._fields[current_groupby]
                .comodel_name
            )
        else:
            groupby_model = None

        _debug.logic(
            "groupby_parsed",
            report_line=self,
            current_groupby=current_groupby,
            next_groupby=next_groupby,
            groupby_model=groupby_model,
            custom=current_groupby in custom_groupby_map,
        )
        return {
            "current_groupby": current_groupby,
            "next_groupby": next_groupby,
            "current_groupby_model": groupby_model,
            "custom_groupby_map": custom_groupby_map,
        }

    @_debug.perf.timed
    def action_reset_custom_groupby(self):
        _debug.lifecycle("action_reset_custom_groupby", records=self)
        self.check_singleton()
        self.user_groupby = self.groupby

    def _get_groupby(self, options):
        self.check_singleton()
        if options["export_mode"] == "file":
            return self.groupby
        return self.user_groupby

    def _get_indenting_groupby_models(self):
        """Models whose records, met in a line id, indent the lines under them."""
        return ()

    def _get_groupby_record_state(self, groupby_model, record):
        """The state that marks a grouped record as a draft, or None."""
