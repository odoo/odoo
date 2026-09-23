import contextlib
import io
import json
import mimetypes
import re
from itertools import groupby

import markupsafe

from odoo import _, api, models
from odoo.libs.debug_log import DebugLog
from odoo.libs.documents import SHEETS, SheetBuilder, get_writers, mimetype_for
from odoo.tools.mail import html_to_inner_content
from odoo.tools.misc import file_path

_debug = DebugLog(__name__)

# Side margins are explicit: a company paperformat with margin_left/right at 0 lets a
# table wider than the sheet bleed into the printer's non-printable edge and lose the
# last digit of its widest column.
PDF_PAPERFORMAT_ARGS = {
    "data-report-margin-top": 10,
    "data-report-margin-left": 7,
    "data-report-margin-right": 7,
    "data-report-margin-bottom": 15,
}
XLSX_MEASURE_FONT_SIZE = 12


class AccountReportExport(models.Model):
    _inherit = "report.formula"

    def get_export_mime_type(self, file_type):
        return (
            mimetype_for(file_type)
            or mimetypes.guess_type(f"x.{file_type}")[0]
            or False
        )

    ####################################################
    # OPTIONS: EXPORT
    ####################################################
    def _init_options_export(self, options, previous_options):
        options["report_title"] = previous_options.get("report_title")

    def export_file(self, options, file_generator, next_action=None):
        self.check_singleton()

        export_options = {**options, "export_mode": "file"}
        _debug.pipeline(
            "export_file",
            report=self,
            file_generator=file_generator,
            next=next_action,
        )

        return {
            "type": "ir_actions_account_report_download",
            "data": {
                "options": json.dumps(export_options),
                "file_generator": file_generator,
                "next_action": next_action,
            },
        }

    @_debug.perf.timed
    def export_to_xlsx(self, options, response=None):
        self.check_singleton()
        print_options = self.get_options(
            previous_options={**options, "export_mode": "print"}
        )
        if print_options["sections"]:
            reports_to_print = self.env["report.formula"].browse(
                [section["id"] for section in print_options["sections"]]
            )
        else:
            reports_to_print = self
        _debug.logic(
            "xlsx_reports_selected",
            report=self,
            by_sections=bool(print_options["sections"]),
            reports=reports_to_print,
        )

        sheets = []
        reports_options = []
        for report in reports_to_print:
            report_options = report.get_options(
                previous_options={**print_options, "selected_section_id": report.id}
            )
            reports_options.append(report_options)
            custom_handler_model = report._get_custom_handler_model()
            with _debug.perf(
                "xlsx_sheet",
                cr=self.env.cr,
                report=report,
                custom=custom_handler_model,
            ):
                if custom_handler_model and hasattr(
                    self.env[custom_handler_model], "_get_xlsx_sheets"
                ):
                    sheets += self.env[custom_handler_model]._get_xlsx_sheets(
                        report_options
                    )
                else:
                    sheets.append(report._get_xlsx_sheet(report_options))

        sheets.append(self._get_xlsx_options_sheet(reports_options))
        generated_file = self._write_xlsx_sheets(sheets)
        _debug.pipeline(
            "xlsx_workbook_written",
            report=self,
            sheets=len(reports_options),
            size=len(generated_file),
        )

        return {
            "file_name": self.get_default_report_filename(options, "xlsx"),
            "file_content": generated_file,
            "file_type": "xlsx",
        }

    @api.model
    def _write_xlsx_sheets(self, sheets):
        writer = get_writers(mimetype_for("xlsx"), SHEETS)[0]
        return writer.write(
            sheets,
            measure_fonts=self._get_xlsx_measure_fonts(),
            decimals=self.env.company.currency_id.decimal_places,
        )

    @api.model
    def _get_xlsx_measure_fonts(self):
        fonts = {}
        for font_type in ("Reg", "Bol", "RegIta", "BolIta"):
            with contextlib.suppress(FileNotFoundError):
                fonts[font_type] = file_path(
                    f"web/static/fonts/lato/Lato-{font_type}-webfont.ttf"
                )
        return fonts

    @_debug.perf.timed
    def _get_xlsx_sheet(self, options):
        sheet = SheetBuilder(self.name)

        def write_cell(sheet, x, y, value, style, colspan=1, rowspan=1, datetime=False):
            sheet.cell(
                y,
                x,
                value,
                style,
                rowspan=rowspan,
                colspan=colspan,
                date=datetime,
                measure=XLSX_MEASURE_FONT_SIZE,
            )

        default_format_props = {
            "font_name": "Lato",
            "font_size": 12,
            "font_color": "#666666",
            "num_format": "#,##0.00",
        }
        text_format_props = {
            "font_name": "Lato",
            "font_size": 12,
            "font_color": "#666666",
        }
        date_format_props = {
            "font_name": "Lato",
            "font_size": 12,
            "font_color": "#666666",
            "align": "left",
            "num_format": "yyyy-mm-dd",
        }
        title_format = {"font_name": "Lato", "font_size": 12, "bold": True, "bottom": 2}
        annotation_format = {**text_format_props, "text_wrap": True}
        workbook_formats = {
            0: {
                "default": {
                    **default_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 6,
                },
                "text": {
                    **text_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 6,
                },
                "date": {
                    **date_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 6,
                },
                "total": {
                    **default_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 6,
                },
            },
            1: {
                "default": {
                    **default_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 1,
                },
                "text": {
                    **text_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 1,
                },
                "date": {
                    **date_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 1,
                },
                "total": {
                    **default_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 1,
                },
                "default_indent": {
                    **default_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 1,
                    "indent": 1,
                },
                "date_indent": {
                    **date_format_props,
                    "bold": True,
                    "font_size": 13,
                    "bottom": 1,
                    "indent": 1,
                },
            },
            2: {
                "default": {**default_format_props, "bold": True},
                "text": {**text_format_props, "bold": True},
                "date": {**date_format_props, "bold": True},
                "initial": dict(default_format_props),
                "total": {**default_format_props, "bold": True},
                "default_indent": {**default_format_props, "bold": True, "indent": 2},
                "date_indent": {**date_format_props, "bold": True, "indent": 2},
                "initial_indent": {**default_format_props, "indent": 2},
                "total_indent": {**default_format_props, "bold": True, "indent": 1},
            },
            "default": {
                "default": dict(default_format_props),
                "text": dict(text_format_props),
                "date": dict(date_format_props),
                "total": dict(default_format_props),
                "default_indent": {**default_format_props, "indent": 2},
                "date_indent": {**date_format_props, "indent": 2},
                "total_indent": {**default_format_props, "indent": 2},
            },
        }

        def get_format(content_type="default", level="default"):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats["default"],
                    "default_indent": {**default_format_props, "indent": level},
                    "date_indent": {**date_format_props, "indent": level},
                    "total_indent": {
                        **default_format_props,
                        "bold": True,
                        "indent": level - 1,
                    },
                }

            level_formats = workbook_formats[level]
            if "_indent" in content_type and not level_formats.get(content_type):
                return level_formats.get(
                    "default_indent",
                    level_formats.get(
                        content_type.removesuffix("_indent"), level_formats["default"]
                    ),
                )
            return level_formats.get(content_type, level_formats["default"])

        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))
        report_annotations = self.get_annotations(options, lines)
        _debug.pipeline(
            "xlsx_lines_fetched",
            report=self,
            lines=len(lines),
            annotated_lines=len(report_annotations),
        )

        # For reports with lines generated for accounts, the account name and codes are shown in a single column.
        # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
        account_lines_split_names = {}
        for line in lines:
            split_name = self._split_line_name_for_xlsx(line)
            if split_name:
                account_lines_split_names[line["id"]] = split_name

        # Set the (Account) Name column width to 50.
        # If we have account lines and split the name and code in two columns, we will also set the code column.
        if len(account_lines_split_names) > 0:
            sheet.column(0, 0, 13)
            sheet.column(1, 1, 50)
        else:
            sheet.column(0, 0, 50)

        _debug.logic(
            "xlsx_columns_layout",
            report=self,
            account_code_split=len(account_lines_split_names),
            currency_code_columns=not options.get("no_xlsx_currency_code_columns"),
        )
        if not options.get("no_xlsx_currency_code_columns"):
            self._add_xlsx_currency_codes_columns(options, lines)

        # keep tracks of cells merged vertically
        merged_rowspan_cells = set()

        original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

        y_offset = 0
        # 1 and not 0 to leave space for the line name. original_x_offset allows making place for the code column if needed.
        x_offset = original_x_offset + 1

        # Add headers.
        # For this, iterate in the same way as done in main_table_header template
        column_headers_render_data = self._prepare_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options["column_headers"]):
            for header_to_render in (
                header_level
                * column_headers_render_data["level_repetitions"][header_level_index]
            ):
                colspan = header_to_render.get(
                    "colspan",
                    column_headers_render_data["level_colspan"][header_level_index],
                )
                colspan_with_horizontal_group = colspan + (
                    1
                    if options["show_horizontal_group_total"]
                    and header_level_index == 0
                    else 0
                )
                rowspan = (
                    len(options["column_headers"]) - 1
                    if header_to_render.get("forced_options", {}).get(
                        "no_subheader_division"
                    )
                    else 1
                )

                while (x_offset, y_offset) in merged_rowspan_cells:
                    x_offset += 1

                write_cell(
                    sheet,
                    x_offset,
                    y_offset,
                    header_to_render.get("name", ""),
                    title_format,
                    colspan_with_horizontal_group,
                    rowspan=rowspan,
                )

                # tracks cells merged vertically
                if rowspan > 1:
                    for row in range(1, rowspan):
                        merged_rowspan_cells.update(
                            (x_offset + col, y_offset + row)
                            for col in range(colspan_with_horizontal_group)
                        )

                x_offset += colspan
            if options.get("column_percent_comparison") in (
                "growth",
                "analytic_coverage",
            ):
                write_cell(sheet, x_offset, y_offset, "%", title_format)
                x_offset += 1

            if options["show_horizontal_group_total"] and header_level_index != 0:
                horizontal_group_name = next(
                    (
                        group["name"]
                        for group in options["available_horizontal_groups"]
                        if group["id"] == options["selected_horizontal_group_id"]
                    ),
                    None,
                )
                write_cell(
                    sheet, x_offset, y_offset, horizontal_group_name, title_format
                )
                x_offset += 1
            if report_annotations:
                annotations_x_offset = x_offset
                write_cell(
                    sheet, annotations_x_offset, y_offset, "Annotations", title_format
                )
                x_offset += 1
            y_offset += 1
            x_offset = original_x_offset + 1

        for subheader in column_headers_render_data["custom_subheaders"]:
            colspan = subheader.get("colspan", 1)
            write_cell(
                sheet,
                x_offset,
                y_offset,
                subheader.get("name", ""),
                title_format,
                colspan,
            )
            x_offset += colspan
        y_offset += 1
        x_offset = original_x_offset + 1

        if account_lines_split_names:
            # If we have a separate account code column, add a title for it
            write_cell(sheet, x_offset - 2, y_offset, _("Code"), title_format)
            write_cell(sheet, x_offset - 1, y_offset, _("Account Name"), title_format)
        sheet.column(x_offset, x_offset + len(options["columns"]), 10)

        for column in options["columns"]:
            colspan = column.get("colspan", 1)
            write_cell(
                sheet, x_offset, y_offset, column.get("name", ""), title_format, colspan
            )
            x_offset += colspan

        if options["show_horizontal_group_total"]:
            write_cell(
                sheet,
                x_offset,
                y_offset,
                options["columns"][0].get("name", ""),
                title_format,
                colspan,
            )

        if options.get("column_percent_comparison") in ("growth", "analytic_coverage"):
            write_cell(sheet, x_offset, y_offset, "", title_format, colspan)
        y_offset += 1

        if options.get("order_column"):
            lines = self.sort_lines(lines, options)

        # Disable bold styling for the max level.
        max_level = max(line.get("level", -1) for line in lines) if lines else -1
        _debug.logic(
            "xlsx_max_level_unbolded",
            report=self,
            max_level=max_level,
            applied=max_level in {0, 1, 2},
            sorted=bool(options.get("order_column")),
            header_rows=y_offset,
        )
        if max_level in {0, 1, 2}:
            # Total lines are supposed to be a level above, so we don't touch them.
            for wb_format in (
                s for s in workbook_formats[max_level] if "total" not in s
            ):
                workbook_formats[max_level][wb_format]["bold"] = False

        # Add lines.
        counter = 1
        for y, line in enumerate(lines):
            level = line.get("level")
            if level == 0:
                y_offset += 1
            elif not level:
                level = "default"

            line_id = self._parse_line_id(line.get("id"))
            is_initial_line = line_id[-1][0] == "initial" if line_id else False
            is_total_line = line_id[-1][0] == "total" if line_id else False

            # Write the first column(s), with a specific style to manage the indentation.
            cell_type, cell_value = self._get_cell_type_value(line)
            account_code_cell_format = get_format("text", level)

            if cell_type == "date":
                cell_format = get_format("date_indent", level)
            elif is_initial_line:
                cell_format = get_format("initial_indent", level)
            elif is_total_line:
                cell_format = get_format("total_indent", level)
            else:
                cell_format = get_format("default_indent", level)

            x_offset = original_x_offset + 1
            if line["id"] in account_lines_split_names:
                # Write the Account Code and Name columns.
                code, name = account_lines_split_names[line["id"]]
                # Don't indent the account code and don't format is as a monetary value either.
                write_cell(sheet, 0, y + y_offset, code, account_code_cell_format)
                write_cell(sheet, 1, y + y_offset, name, cell_format)
            else:
                write_cell(
                    sheet,
                    original_x_offset,
                    y + y_offset,
                    cell_value,
                    cell_format,
                    datetime=cell_type == "date",
                )

                if (
                    "parent_id" in line
                    and line["parent_id"] in account_lines_split_names
                ):
                    write_cell(
                        sheet,
                        1 + original_x_offset,
                        y + y_offset,
                        account_lines_split_names[line["parent_id"]][0],
                        account_code_cell_format,
                    )
                elif account_lines_split_names:
                    write_cell(
                        sheet,
                        1 + original_x_offset,
                        y + y_offset,
                        "",
                        account_code_cell_format,
                    )

            # Write all the remaining cells.
            columns = line["columns"]
            if (
                options.get("column_percent_comparison")
                and "column_percent_comparison_data" in line
            ):
                columns += [line["column_percent_comparison_data"]]

            if options["show_horizontal_group_total"]:
                columns += [line.get("horizontal_group_total_data", {"name": 0})]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)
                if cell_type == "date":
                    cell_format = get_format("date", level)
                elif is_initial_line:
                    cell_format = get_format("initial", level)
                elif is_total_line:
                    cell_format = get_format("total", level)
                else:
                    cell_format = get_format("default", level)
                write_cell(
                    sheet,
                    x + line.get("colspan", 1) - 1,
                    y + y_offset,
                    cell_value,
                    cell_format,
                    datetime=cell_type == "date",
                )

            # Write annotations.
            if report_annotations and (
                line_annotations := report_annotations.get(line["id"])
            ):
                line_annotation_text = []
                record_to_number_map = {}
                for line_annotation in line_annotations:
                    if (
                        line_annotation["model"],
                        line_annotation["id"],
                    ) in record_to_number_map:
                        counter = record_to_number_map[
                            line_annotation["model"], line_annotation["id"]
                        ]
                    else:
                        counter = len(record_to_number_map) + 1
                        record_to_number_map[
                            line_annotation["model"], line_annotation["id"]
                        ] = counter

                    line_annotation_text.append(
                        f"{counter} - {html_to_inner_content(line_annotation['body'])}"
                    )
                write_cell(
                    sheet,
                    annotations_x_offset,
                    y + y_offset,
                    "\n".join(line_annotation_text),
                    annotation_format,
                )
        _debug.pipeline(
            "xlsx_sheet_written",
            report=self,
            lines=len(lines),
            columns=len(options["columns"]),
        )
        return sheet

    @_debug.perf.timed
    def _add_xlsx_currency_codes_columns(self, options, lines):
        required_currency_code_columns = {
            label.removeprefix("_currency_")
            for label in self.line_ids.expression_ids.mapped("label")
            if label.startswith("_currency_")
        }

        new_columns = []
        for col in options["columns"]:
            new_columns.append(col)

            if col["expression_label"] in required_currency_code_columns:
                new_columns.append(
                    {
                        **col,
                        "name": _("Currency Code"),
                        "figure_type": "string",
                        "expression_label": f"_xlsx_currency_code_{col['expression_label']}",
                    }
                )

        options["columns"] = new_columns
        _debug.pipeline(
            "xlsx_currency_columns_added",
            report=self,
            currency_labels=len(required_currency_code_columns),
            columns=len(new_columns),
            lines=len(lines),
        )

        # Add 'Currency Code' values to each line
        for line in lines:
            new_column_values = []

            for index, col_data in enumerate(line["columns"]):
                new_column_values.append(col_data)

                if col_data.get("expression_label") in required_currency_code_columns:
                    currency = col_data.get("currency")
                    currency_code = currency.name if currency else ""
                    new_column = self._prepare_column_dict(
                        currency_code, options["columns"][index + 1], options
                    )
                    new_column["name"] = new_column["no_format"]
                    new_column_values.append(new_column)

            line["columns"] = new_column_values

    @_debug.perf.timed
    def _get_xlsx_options_sheet(self, options_list):
        """A sheet summarising every filter and option active at the moment of the export."""
        filters_sheet = SheetBuilder(_("Filters"))
        filters_sheet.column(0, 0, 20)
        filters_sheet.column(1, 1, 50)
        name_style = {"font_name": "Arial", "bold": True, "bottom": 2}
        y_offset = 0

        if len(options_list) == 1:
            _debug.logic("options_sheet_single_report", report=self)
            self.env["report.formula"].browse(
                options_list[0]["report_id"]
            )._write_report_options_to_xlsx_sheet(
                options_list[0], filters_sheet, y_offset
            )
            return filters_sheet

        # Find uncommon keys
        options_sets = list(map(set, options_list))
        common_keys = set.intersection(*options_sets)
        all_keys = set.union(*options_sets)
        uncommon_options_keys = all_keys - common_keys
        # Try to find the common filter values between all reports to avoid duplication.
        common_options_values = {}
        for key in common_keys:
            first_value = options_list[0][key]
            if all(options[key] == first_value for options in options_list[1:]):
                common_options_values[key] = first_value
            else:
                uncommon_options_keys.add(key)
        _debug.pipeline(
            "options_sheet_keys_split",
            report=self,
            reports=len(options_list),
            common=len(common_options_values),
            uncommon=len(uncommon_options_keys),
        )

        # Write common options to the sheet.
        filters_sheet.cell(y_offset, 0, _("All"), name_style)
        y_offset += 1
        y_offset = self._write_report_options_to_xlsx_sheet(
            common_options_values, filters_sheet, y_offset
        )

        for report_options in options_list:
            report = self.env["report.formula"].browse(report_options["report_id"])

            filters_sheet.cell(y_offset, 0, report.name, name_style)
            y_offset += 1
            new_offset = report._write_report_options_to_xlsx_sheet(
                report_options, filters_sheet, y_offset, uncommon_options_keys
            )

            if y_offset == new_offset:
                y_offset -= 1
                # Clear the report name's cell since it didn't add any data to the xlsx.
                filters_sheet.cell(y_offset, 0, " ")
            else:
                y_offset = new_offset
        return filters_sheet

    @_debug.perf.timed
    def _write_report_options_to_xlsx_sheet(
        self, options, sheet, y_offset, options_to_print=None
    ):
        def write_filter_lines(filter_title, filter_lines, y_offset):
            sheet.cell(y_offset, 0, filter_title)
            for line in filter_lines:
                sheet.cell(y_offset, 1, line)
                y_offset += 1
            return y_offset

        def is_option_printable(option_key):
            """Check if the option should be printed based on options_to_print."""
            return not options_to_print or option_key in options_to_print

        start_y_offset = y_offset  # debuglog
        for _sequence, option_key, title, lines in sorted(
            self._get_xlsx_printable_filters(options, options_to_print),
            key=lambda entry: entry[0],
        ):
            if lines and (option_key is None or is_option_printable(option_key)):
                y_offset = write_filter_lines(title, lines, y_offset)

        _debug.pipeline(
            "report_options_written",
            report=self,
            rows=y_offset - start_y_offset,
            restricted=bool(options_to_print),
        )
        return y_offset

    def get_default_report_filename(self, options, extension):
        """The default to be used for the file when downloading pdf,xlsx,..."""
        self.check_singleton()
        if title := options.get("report_title"):
            _debug.logic("filename_from_title", report=self, extension=extension)
            return title
        if "sections_source_id" not in options:
            _debug.logic("filename_generic", report=self, extension=extension)
            return _("report.%(file_extension)s", file_extension=extension)

        def _transform_period(period=""):
            if dates := re.findall(r"\d{2}/\d{2}/\d{4}", period):
                return f"{'_'.join(dates).replace('/', '')}"
            # We replace _-_ to handle periods with type 'quarter'
            return f"{period.replace(' ', '_').replace('_-_', '_').lower()}"

        def _get_company_name(companies):
            if companies and len(companies) == 1:
                return f"_{companies[0]['name'].replace(' ', '_').lower()}"
            return ""

        period = options.get("date", {}).get("string")
        sections_source_id = options["sections_source_id"]
        if sections_source_id != self.id:
            sections_source = self.env["report.formula"].browse(sections_source_id)
        else:
            sections_source = self

        _debug.logic(
            "filename_from_sections",
            report=self,
            sections_source=sections_source,
            extension=extension,
        )
        return f"{sections_source.name.lower().replace(' ', '_')}_{_transform_period(period)}{_get_company_name(options['companies'])}.{extension}"

    @_debug.perf.timed
    def export_to_pdf(self, options):
        self.check_singleton()

        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "report.url"
        ) or self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        rcontext = {
            "mode": "print",
            "base_url": base_url,
            "company": self.env.company,
        }

        print_options = self.get_options(
            previous_options={**options, "export_mode": "print"}
        )
        if print_options["sections"]:
            reports_to_print = self.env["report.formula"].browse(
                [section["id"] for section in print_options["sections"]]
            )
        else:
            reports_to_print = self
        _debug.logic(
            "pdf_reports_selected",
            report=self,
            by_sections=bool(print_options["sections"]),
            reports=reports_to_print,
        )

        reports_options = []
        reports_options.extend(
            report.get_options(
                previous_options={**print_options, "selected_section_id": report.id}
            )
            for report in reports_to_print
        )

        grouped_reports_by_format = groupby(
            zip(reports_to_print, reports_options, strict=False),
            key=lambda report: (
                len(report[1]["columns"]) > 5 or report[1].get("horizontal_split")
            ),
        )

        footer = self._get_layout_footer(rcontext)

        action_report = self.env["ir.actions.report"].with_context(
            account_report_pdf_export=True
        )
        files_stream = []
        for is_landscape, reports_with_options in grouped_reports_by_format:
            bodies = []

            for report, report_options in reports_with_options:
                # Use custom handler's PDF export method if available
                custom_handler_model = report._get_custom_handler_model()
                handler = (
                    self.env[custom_handler_model]
                    if (
                        custom_handler_model
                        and hasattr(
                            self.env[custom_handler_model], "_get_pdf_export_html"
                        )
                    )
                    else report
                )
                _debug.logic(
                    "pdf_handler_chosen",
                    report=report,
                    custom_handler=custom_handler_model,
                    handler=handler,
                )
                bodies.append(
                    handler._get_pdf_export_html(
                        report_options,
                        report._filter_out_folded_children(
                            report._get_lines(report_options)
                        ),
                        additional_context={"base_url": base_url},
                    )
                )

            bodies_list = [
                action_report._get_html_with_header_footer(body, footer=footer)
                if footer
                else body
                for body in bodies
            ]
            with _debug.perf(
                "pdf_render",
                cr=self.env.cr,
                report=self,
                bodies_list_count=len(bodies_list),
                landscape=is_landscape,
            ):
                files_stream.append(
                    io.BytesIO(
                        action_report._render_html_to_pdf(
                            bodies_list,
                            landscape=is_landscape
                            or self.env.context.get("force_landscape_printing"),
                            specific_paperformat_args=PDF_PAPERFORMAT_ARGS,
                        )
                    )
                )

        _debug.pipeline(
            "pdf_streams_rendered",
            report=self,
            streams=len(files_stream),
            merged=len(files_stream) > 1,
            has_footer=bool(footer),
        )
        if len(files_stream) > 1:
            result_stream = action_report._merge_pdfs(files_stream)
            result = result_stream.getvalue()
            # Close the different stream
            result_stream.close()
            for file_stream in files_stream:
                file_stream.close()
        else:
            result = files_stream[0].read()

        return {
            "file_name": self.get_default_report_filename(options, "pdf"),
            "file_content": result,
            "file_type": "pdf",
        }

    @_debug.perf.timed
    def _get_pdf_export_html(
        self, options, lines, additional_context=None, template=None
    ):
        report_info = self.get_report_information(options)

        custom_print_templates = options["custom_display_config"].get("pdf_export", {})
        template = custom_print_templates.get(
            "pdf_export_main", "report_formula.pdf_export_main"
        )

        render_values = {
            "report": self,
            "report_title": options.get("report_title") or self.name,
            "options": options,
            "table_start": markupsafe.Markup("<tbody>"),
            "table_end": markupsafe.Markup("""
                </tbody></table></div>
                <div style="page-break-after: always"></div>
                <div class="d-flex align-items-start">
                <table class="o_table">
            """),
            "column_headers_render_data": self._prepare_column_headers_render_data(
                options
            ),
            "custom_templates": custom_print_templates,
        }
        if additional_context:
            render_values.update(additional_context)

        if options.get("order_column"):
            lines = self.sort_lines(lines, options)

        lines = self._format_lines_for_display(lines, options)
        _debug.pipeline(
            "pdf_html_lines_formatted",
            report=self,
            template=template,
            lines=len(lines),
            sorted=bool(options.get("order_column")),
            last_annotations=bool(options.get("show_last_annotations")),
        )

        render_values["lines"] = lines
        render_values.update(
            self._get_pdf_export_render_values(options, lines, report_info)
        )

        options["css_custom_class"] = options["custom_display_config"].get(
            "css_custom_class", ""
        )

        # Render.
        return self.env["ir.qweb"]._render(template, render_values)

    def _get_layout_footer(self, rcontext):
        if self.env.context.get("exclude_page_footer"):
            return None
        else:
            footer_html = self.env["ir.actions.report"]._render_template(
                self._get_pdf_footer_template(), values=rcontext
            )
            footer_html = self.env["ir.actions.report"]._render_template(
                "web.minimal_layout",
                values=dict(
                    rcontext, subst=True, body=markupsafe.Markup(footer_html.decode())
                ),
            )
            return footer_html.decode()

    def _get_pdf_footer_template(self):
        return "web.internal_layout"

    def _get_pdf_export_render_values(self, options, lines, report_info):
        return {
            "extra_option_labels": self._get_pdf_extra_option_labels(options),
            "totals_below_sections": self._get_totals_below_sections(),
        }

    def _get_pdf_extra_option_labels(self, options):
        rounding_unit_label = options["rounding_unit_names"][options["rounding_unit"]][
            1
        ]
        return [rounding_unit_label] if rounding_unit_label else []

    def _split_line_name_for_xlsx(self, line):
        return None

    def _get_xlsx_printable_filters(self, options, options_to_print=None):
        companies = options["companies"]
        filters = [
            (
                10,
                "companies",
                _("Companies") if len(companies) > 1 else _("Company"),
                [company["name"] for company in companies],
            ),
            (
                30,
                "selected_partner_ids",
                _("Partners"),
                options.get("selected_partner_ids"),
            ),
            (
                40,
                "selected_partner_categories",
                _("Partner Categories"),
                options.get("selected_partner_categories"),
            ),
        ]
        if group_id := options.get("selected_horizontal_group_id"):
            filters.append(
                (
                    50,
                    "selected_horizontal_group_id",
                    _("Horizontal Group"),
                    [
                        group["name"]
                        for group in options["available_horizontal_groups"]
                        if group["id"] == group_id
                    ][:1],
                )
            )
        if options.get("company_currency"):
            filters.append(
                (
                    60,
                    "company_currency",
                    _("Company Currency"),
                    [options["company_currency"]["currency_name"]],
                )
            )
        return filters
