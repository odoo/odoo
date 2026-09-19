import base64
import contextlib
import datetime
import io
import json
import mimetypes
import re
from ast import literal_eval
from collections import defaultdict
from itertools import groupby

import markupsafe
from PIL import ImageFont

from odoo import _, api, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.documents import mimetype_for
from odoo.libs.numbers import float_repr
from odoo.tools import html2plaintext
from odoo.tools.mail import html_to_inner_content
from odoo.tools.misc import file_path, format_date

from .account_report import (
    ACCOUNT_CODES_ENGINE_SPLIT_REGEX,
    ACCOUNT_CODES_ENGINE_TERM_REGEX,
)
from .account_report_engine import (
    ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX,
    AccountReportFileDownloadException,
)

_debug = DebugLog(__name__)

# Side margins are explicit: a company paperformat with margin_left/right at 0 lets a
# table wider than the sheet bleed into the printer's non-printable edge and lose the
# last digit of its widest column. No data-report-header-spacing: WeasyPrint has no
# equivalent and logs a warning per render.
PDF_PAPERFORMAT_ARGS = {
    "data-report-margin-top": 10,
    "data-report-margin-left": 7,
    "data-report-margin-right": 7,
    "data-report-margin-bottom": 15,
}


class AccountReportExport(models.Model):
    _inherit = "account.report"

    @api.model
    @_debug.perf.timed
    def _cron_account_report_send(self, job_count=10):
        """Handle Send & Print async processing.
        :param job_count: maximum number of jobs to process if specified.
        """
        _debug.lifecycle("_cron_account_report_send", records=self)
        to_process = self.env["account.report"].search(
            [("send_and_print_values", "!=", False)],
        )
        if not to_process:
            _debug.logic("send_skipped", reason="nothing_queued", job_count=job_count)
            return

        _debug.pipeline("send_queue_loaded", reports=to_process, job_count=job_count)
        processed_count = 0
        need_retrigger = False

        for report in to_process:
            if need_retrigger:
                break
            send_and_print_vals = report.send_and_print_values
            report_partner_ids = send_and_print_vals.get("report_options", {}).get(
                "partner_ids", []
            )
            need_retrigger = processed_count + len(report_partner_ids) > job_count
            partner_ids = report_partner_ids[: job_count - processed_count]
            company = self.env["res.company"].browse(
                send_and_print_vals["report_options"]["companies"][0]["id"]
            )
            existing_partner_ids = set(
                self.env["res.partner"].browse(partner_ids).exists().ids
            )
            for partner_id in partner_ids:
                if partner_id in existing_partner_ids:
                    options = {
                        **send_and_print_vals["report_options"],
                        "partner_ids": [partner_id],
                    }
                    self.env["account.report.send"]._process_send_and_print(
                        report=report.with_company(company), options=options
                    )
                    processed_count += 1
                report_partner_ids.remove(partner_id)
            _debug.pipeline(
                "report_send_batch",
                report=report,
                partners=len(partner_ids),
                existing_partners=len(existing_partner_ids),
                remaining_partners=len(report_partner_ids),
                processed=processed_count,
                need_retrigger=need_retrigger,
            )
            if report_partner_ids:
                send_and_print_vals["report_options"]["partner_ids"] = (
                    report_partner_ids
                )
                report.send_and_print_values = send_and_print_vals
            else:
                report.send_and_print_values = False

        _debug.logic(
            "send_retrigger_decided",
            need_retrigger=need_retrigger,
            processed=processed_count,
            job_count=job_count,
        )
        if need_retrigger:
            self.env.ref("account.ir_cron_account_report_send")._trigger()

    def get_export_mime_type(self, file_type):
        """Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        # Six of the seven entries this replaced restated what `mimetypes`
        # already answers, and the seventh said an `xaf` -- a Dutch audit file,
        # which is XML -- was an OpenOffice Writer document. A format the
        # workspace registers wins; anything else is a filename question the
        # standard library has answered since before this table was written.
        return (
            mimetype_for(file_type)
            or mimetypes.guess_type(f"x.{file_type}")[0]
            or False
        )

    ####################################################
    # OPTIONS: EXPORT
    ####################################################
    def _init_options_export_mode(self, options, previous_options):
        options["export_mode"] = previous_options.get("export_mode")

    def _init_options_export(self, options, previous_options):
        options["report_title"] = previous_options.get("report_title")

    @api.model
    def _get_sender_company_for_export(self, options):
        """Return the sender company when generating an export file from this report.
        :return: self.env.company if not using a tax unit, else the main company of that unit
        """
        if options.get("tax_unit", "company_only") != "company_only":
            tax_unit = self.env["account.tax.unit"].browse(options["tax_unit"])
            _debug.logic("sender_company_tax_unit", tax_unit=tax_unit)
            return tax_unit.main_company_id

        report_companies = self.env["res.company"].browse(
            self.get_report_company_ids(options)
        )
        options_main_company = report_companies[0]

        if (
            options.get("tax_unit") is not None
            and options_main_company._get_branches_with_same_vat() == report_companies
        ):
            # The line with the smallest number of parents in the VAT sub-hierarchy is assumed to be the root
            _debug.logic("sender_company_vat_root", companies=report_companies)
            return report_companies.sorted(lambda x: len(x.parent_ids))[0]
        elif options_main_company._is_every_branch_selected():
            _debug.logic("sender_company_branch_root", company=options_main_company)
            return options_main_company.root_id

        _debug.logic("sender_company_main", company=options_main_company)
        return options_main_company

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
    def _get_report_send_recipients(self, options):
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model and hasattr(
            self.env[custom_handler_model], "_get_report_send_recipients"
        ):
            return self.env[custom_handler_model]._get_report_send_recipients(options)
        return self.env["res.partner"]

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
            reports_to_print = self.env["account.report"].browse(
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
            "pdf_export_main", "account.pdf_export_main"
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

        # Manage annotations.
        render_values["show_last_annotations"] = options.get("show_last_annotations")
        render_values["status_selection"] = dict(
            self.env["account.audit.account.status"]
            ._fields["status"]
            ._description_selection(self.env)
        )
        if options.get("show_last_annotations"):
            last_annotations = self._get_last_comments_by_line(options, lines)
            for line in lines:
                line["last_comment"] = last_annotations.get(line["id"])
        else:
            render_values["annotations"] = (
                self._prepare_annotations_list_for_pdf_export(
                    options["date"], lines, report_info["annotations"]
                )
            )

        options["css_custom_class"] = options["custom_display_config"].get(
            "css_custom_class", ""
        )

        # Render.
        return self.env["ir.qweb"]._render(template, render_values)

    @_debug.perf.timed
    def _prepare_annotations_list_for_pdf_export(
        self, date_options, lines, annotations_per_line_id
    ):
        annotations_to_render = []
        record_to_number_map = {}
        for line in lines:
            line["annotations"] = []
            for annotation in annotations_per_line_id.get(line["id"], []):
                report_period_date_from = datetime.datetime.strptime(
                    date_options["date_from"], "%Y-%m-%d"
                ).date()
                report_period_date_to = datetime.datetime.strptime(
                    date_options["date_to"], "%Y-%m-%d"
                ).date()
                if (
                    not annotation["date"]
                    or report_period_date_from
                    <= annotation["date"]
                    <= report_period_date_to
                ):
                    if number := record_to_number_map.get(
                        (annotation["model"], annotation["id"])
                    ):
                        line["annotations"].append(str(number))
                        continue
                    number = len(record_to_number_map) + 1
                    record_to_number_map[annotation["model"], annotation["id"]] = number
                    line["annotations"].append(str(number))
                    annotations_to_render.append(
                        {
                            "number": str(number),
                            # wkhtmltopdf adds a <br> before tags such as p and div. This makes the first line of the body go down one line.
                            # we are losing some formatting here, but annotations shouldn't have complicated tags in them.
                            "body": markupsafe.Markup("<br/>").join(
                                html2plaintext(annotation["body"]).split("\n")
                            ),
                            "date": format_date(self.env, annotation["date"])
                            if annotation["date"]
                            else None,
                        }
                    )
        _debug.pipeline(
            "pdf_annotations_prepared",
            lines=len(lines),
            annotated_lines=len(annotations_per_line_id),
            annotations=len(annotations_to_render),
        )
        return annotations_to_render

    @_debug.perf.timed
    def export_to_xlsx(self, options, response=None):
        def add_worksheet_unique_name(workbook, sheet_name):
            existing_names = set(workbook.sheetnames.keys())
            count = 1
            max_length = 31
            new_sheet_name = sheet_name[:max_length]

            while new_sheet_name in existing_names:
                suffix = f" ({count})"
                truncated_name = sheet_name[: max_length - len(suffix)]
                new_sheet_name = f"{truncated_name}{suffix}"
                count += 1
            return workbook.add_worksheet(new_sheet_name)

        self.check_singleton()
        output = io.BytesIO()
        import xlsxwriter

        with xlsxwriter.Workbook(
            output,
            {
                "in_memory": True,
                "strings_to_formulas": False,
            },
        ) as workbook:
            print_options = self.get_options(
                previous_options={**options, "export_mode": "print"}
            )
            if print_options["sections"]:
                reports_to_print = self.env["account.report"].browse(
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

            reports_options = []
            for report in reports_to_print:
                report_options = report.get_options(
                    previous_options={**print_options, "selected_section_id": report.id}
                )
                reports_options.append(report_options)
                # Use custom handler's XLSX export method if available
                custom_handler_model = report._get_custom_handler_model()
                with _debug.perf(
                    "xlsx_sheet",
                    cr=self.env.cr,
                    report=report,
                    custom=custom_handler_model,
                ):
                    if custom_handler_model and hasattr(
                        self.env[custom_handler_model], "_write_report_to_xlsx_sheet"
                    ):
                        self.env[custom_handler_model]._write_report_to_xlsx_sheet(
                            report_options, workbook
                        )
                    else:
                        report._write_report_to_xlsx_sheet(
                            report_options,
                            workbook,
                            add_worksheet_unique_name(workbook, report.name),
                        )

            self._add_options_xlsx_sheet(workbook, reports_options)

        output.seek(0)
        generated_file = output.read()
        output.close()
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
    @_debug.perf.timed
    def _set_xlsx_cell_sizes(self, sheet, fonts, col, row, value, style, has_colspan):
        """This small helper will resize the cells if needed, to allow to get a better output."""

        def get_string_width(font, string):
            return font.getlength(string) / 5

        # Get the correct font for the row style
        font_type = ("Bol" if style.bold else "Reg") + ("Ita" if style.italic else "")
        report_font = fonts[font_type]

        # 8.43 is the default width of a column in Excel.
        try:
            col_width = sheet.col_info[col][0]
        except KeyError:
            col_width = 8.43

        if value is None:
            value = ""
        else:
            # This is needed, otherwise we could compute width on very long number such as 12.0999999998
            # which wouldn't show well in the end result as the numbers are rounded.
            with contextlib.suppress(ValueError, OverflowError):
                value = float_repr(
                    float(value), self.env.company.currency_id.decimal_places
                )

        # Start by computing the width of the cell if we are not using colspans.
        if not has_colspan:
            # Ensure to take indents into account when computing the width.
            formatted_value = f"{'  ' * style.indent}{value}"
            width = get_string_width(
                report_font,
                max(
                    formatted_value.split("\n"),
                    key=lambda line: get_string_width(report_font, line),
                ),
            )
            # We set the width if it is bigger than the current one, with a limit at 75 (max to avoid taking excessive space).
            if width > col_width:
                sheet.set_column(
                    col, col, min(width + 4, 75)
                )  # We need to add a little extra padding to ensure our columns are not clipping the text

    def _get_xlsx_export_fonts(self):
        """Get the bold, italic and regular LATO font information so that we can use them for format purposes."""
        fonts = {}
        for font_type in ("Reg", "Bol", "RegIta", "BolIta"):
            try:
                lato_path = f"web/static/fonts/lato/Lato-{font_type}-webfont.ttf"
                fonts[font_type] = ImageFont.truetype(file_path(lato_path), 12)
            except OSError, FileNotFoundError:
                # This won't give great result, but it will work.
                fonts[font_type] = ImageFont.load_default()
        return fonts

    @_debug.perf.timed
    def _write_report_to_xlsx_sheet(self, options, workbook, sheet):
        fonts = self._get_xlsx_export_fonts()

        def write_cell(sheet, x, y, value, style, colspan=1, rowspan=1, datetime=False):
            self._set_xlsx_cell_sizes(sheet, fonts, x, y, value, style, colspan > 1)
            if colspan == 1 and rowspan == 1:
                if datetime:
                    sheet.write_datetime(y, x, value, style)
                else:
                    sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y + rowspan - 1, x + colspan - 1, value, style)

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
        title_format = workbook.add_format(
            {"font_name": "Lato", "font_size": 12, "bold": True, "bottom": 2}
        )
        annotation_format = workbook.add_format(
            {**text_format_props, "text_wrap": True}
        )
        workbook_formats = {
            0: {
                "default": workbook.add_format(
                    {**default_format_props, "bold": True, "font_size": 13, "bottom": 6}
                ),
                "text": workbook.add_format(
                    {**text_format_props, "bold": True, "font_size": 13, "bottom": 6}
                ),
                "date": workbook.add_format(
                    {**date_format_props, "bold": True, "font_size": 13, "bottom": 6}
                ),
                "total": workbook.add_format(
                    {**default_format_props, "bold": True, "font_size": 13, "bottom": 6}
                ),
            },
            1: {
                "default": workbook.add_format(
                    {**default_format_props, "bold": True, "font_size": 13, "bottom": 1}
                ),
                "text": workbook.add_format(
                    {**text_format_props, "bold": True, "font_size": 13, "bottom": 1}
                ),
                "date": workbook.add_format(
                    {**date_format_props, "bold": True, "font_size": 13, "bottom": 1}
                ),
                "total": workbook.add_format(
                    {**default_format_props, "bold": True, "font_size": 13, "bottom": 1}
                ),
                "default_indent": workbook.add_format(
                    {
                        **default_format_props,
                        "bold": True,
                        "font_size": 13,
                        "bottom": 1,
                        "indent": 1,
                    }
                ),
                "date_indent": workbook.add_format(
                    {
                        **date_format_props,
                        "bold": True,
                        "font_size": 13,
                        "bottom": 1,
                        "indent": 1,
                    }
                ),
            },
            2: {
                "default": workbook.add_format({**default_format_props, "bold": True}),
                "text": workbook.add_format({**text_format_props, "bold": True}),
                "date": workbook.add_format({**date_format_props, "bold": True}),
                "initial": workbook.add_format(default_format_props),
                "total": workbook.add_format({**default_format_props, "bold": True}),
                "default_indent": workbook.add_format(
                    {**default_format_props, "bold": True, "indent": 2}
                ),
                "date_indent": workbook.add_format(
                    {**date_format_props, "bold": True, "indent": 2}
                ),
                "initial_indent": workbook.add_format(
                    {**default_format_props, "indent": 2}
                ),
                "total_indent": workbook.add_format(
                    {**default_format_props, "bold": True, "indent": 1}
                ),
            },
            "default": {
                "default": workbook.add_format(default_format_props),
                "text": workbook.add_format(text_format_props),
                "date": workbook.add_format(date_format_props),
                "total": workbook.add_format(default_format_props),
                "default_indent": workbook.add_format(
                    {**default_format_props, "indent": 2}
                ),
                "date_indent": workbook.add_format({**date_format_props, "indent": 2}),
                "total_indent": workbook.add_format(
                    {**default_format_props, "indent": 2}
                ),
            },
        }

        def get_format(content_type="default", level="default"):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats["default"],
                    "default_indent": workbook.add_format(
                        {**default_format_props, "indent": level}
                    ),
                    "date_indent": workbook.add_format(
                        {**date_format_props, "indent": level}
                    ),
                    "total_indent": workbook.add_format(
                        {**default_format_props, "bold": True, "indent": level - 1}
                    ),
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
            line_model = self._get_model_info_from_id(line["id"])[0]
            if line_model == "account.account":
                # Reuse the _split_code_name to split the name and code in two values.
                account_lines_split_names[line["id"]] = self.env[
                    "account.account"
                ]._split_code_name(line["name"])

        # Set the (Account) Name column width to 50.
        # If we have account lines and split the name and code in two columns, we will also set the code column.
        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 13)
            sheet.set_column(1, 1, 50)
        else:
            sheet.set_column(0, 0, 50)

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
        sheet.set_column(x_offset, x_offset + len(options["columns"]), 10)

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
                workbook_formats[max_level][wb_format].set_bold(False)

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

    @_debug.perf.timed
    def _add_xlsx_currency_codes_columns(self, options, lines):
        """Adds a 'Currency Code' column for each column displaying amounts in foreign currencies. This is done because
        the raw number is displayed on the xlsx file, making it impossible to know the currency used.
        To have it displayed, the line must have an expression label starting with '_currency_'"""
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
    def _add_options_xlsx_sheet(self, workbook, options_list):
        """Adds a new sheet for xlsx report exports with a summary of all filters and options activated at the moment of the export."""
        filters_sheet = workbook.add_worksheet(_("Filters"))
        # Set first and second column widths.
        filters_sheet.set_column(0, 0, 20)
        filters_sheet.set_column(1, 1, 50)
        name_style = workbook.add_format(
            {"font_name": "Arial", "bold": True, "bottom": 2}
        )
        y_offset = 0

        if len(options_list) == 1:
            _debug.logic("options_sheet_single_report", report=self)
            self.env["account.report"].browse(
                options_list[0]["report_id"]
            )._write_report_options_to_xlsx_sheet(
                options_list[0], filters_sheet, y_offset
            )
            return

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
        filters_sheet.write(y_offset, 0, _("All"), name_style)
        y_offset += 1
        y_offset = self._write_report_options_to_xlsx_sheet(
            common_options_values, filters_sheet, y_offset
        )

        for report_options in options_list:
            report = self.env["account.report"].browse(report_options["report_id"])

            filters_sheet.write(y_offset, 0, report.name, name_style)
            y_offset += 1
            new_offset = report._write_report_options_to_xlsx_sheet(
                report_options, filters_sheet, y_offset, uncommon_options_keys
            )

            if y_offset == new_offset:
                y_offset -= 1
                # Clear the report name's cell since it didn't add any data to the xlsx.
                filters_sheet.write(y_offset, 0, " ")
            else:
                y_offset = new_offset

    @_debug.perf.timed
    def _write_report_options_to_xlsx_sheet(
        self, options, sheet, y_offset, options_to_print=None
    ):
        """Inject the report options into the filters sheet.

        :param options: Dictionary containing report options.
        :param sheet: XLSX sheet to inject options into.
        :param y_offset: Offset for the vertical position in the sheet.
        :param options_to_print: Optional list of names to print. If not provided, all printable options will be included.
        """

        def write_filter_lines(filter_title, filter_lines, y_offset):
            sheet.write(y_offset, 0, filter_title)
            for line in filter_lines:
                sheet.write(y_offset, 1, line)
                y_offset += 1
            return y_offset

        def is_option_printable(option_key):
            """Check if the option should be printed based on options_to_print."""
            return not options_to_print or option_key in options_to_print

        start_y_offset = y_offset  # debuglog
        # Company
        if is_option_printable("companies"):
            companies = options["companies"]
            title = _("Companies") if len(companies) > 1 else _("Company")
            lines = [company["name"] for company in companies]
            y_offset = write_filter_lines(title, lines, y_offset)

        # Journals
        if is_option_printable("journals") and (journals := options.get("journals")):
            journal_titles = [
                journal.get("title") for journal in journals if journal.get("selected")
            ]
            if journal_titles:
                y_offset = write_filter_lines(_("Journals"), journal_titles, y_offset)

        # Partners
        if is_option_printable("selected_partner_ids") and (
            partner_names := options.get("selected_partner_ids")
        ):
            y_offset = write_filter_lines(_("Partners"), partner_names, y_offset)

        # Partner categories
        if is_option_printable("selected_partner_categories") and (
            partner_categories := options.get("selected_partner_categories")
        ):
            y_offset = write_filter_lines(
                _("Partner Categories"), partner_categories, y_offset
            )

        # Horizontal groups
        if is_option_printable("selected_horizontal_group_id") and (
            group_id := options.get("selected_horizontal_group_id")
        ):
            for horizontal_group in options["available_horizontal_groups"]:
                if horizontal_group["id"] == group_id:
                    filter_name = horizontal_group["name"]
                    y_offset = write_filter_lines(
                        _("Horizontal Group"), [filter_name], y_offset
                    )
                    break

        # Currency
        if is_option_printable("company_currency") and options.get("company_currency"):
            y_offset = write_filter_lines(
                _("Company Currency"),
                [options["company_currency"]["currency_name"]],
                y_offset,
            )

        # Filters
        if is_option_printable("aml_ir_filters"):
            if options.get("aml_ir_filters") and any(
                opt["selected"] for opt in options["aml_ir_filters"]
            ):
                filter_names = [
                    opt["name"] for opt in options["aml_ir_filters"] if opt["selected"]
                ]
                y_offset = write_filter_lines(_("Filters"), filter_names, y_offset)

        # Extra options
        # Array of tuples for the extra options: (name, option_key, condition)
        extra_options = [
            (_("With Draft Entries"), "all_entries", self.filter_show_draft),
            (_("Unreconciled Entries"), "unreconciled", self.filter_unreconciled),
            (_("Including Analytic Simulations"), "include_analytic_without_aml", True),
        ]
        filter_names = [
            name
            for name, option_key, condition in extra_options
            if (not options_to_print or option_key in options_to_print)
            and condition
            and options.get(option_key)
        ]
        if filter_names:
            y_offset = write_filter_lines(_("Options"), filter_names, y_offset)

        _debug.pipeline(
            "report_options_written",
            report=self,
            rows=y_offset - start_y_offset,
            restricted=bool(options_to_print),
        )
        return y_offset

    @_debug.perf.timed
    def get_vat_for_export(self, options, raise_warning=True):
        """Returns the VAT number to use when exporting this report with the provided
        options. If filter_multi_company is set to 'tax_units', the selected tax unit's VAT
        will be used; else a foreign_vat fiscal position matching the report's country will
        be used if one exists; else the current company's will be, raising an error if its empty.
        """
        self.check_singleton()

        if (
            self.filter_multi_company == "tax_units"
            and options["tax_unit"] != "company_only"
        ):
            tax_unit = self.env["account.tax.unit"].browse(options["tax_unit"])
            _debug.logic(
                "vat_source", report=self, source="tax_unit", tax_unit=tax_unit
            )
            return tax_unit.vat

        company = self._get_sender_company_for_export(options)

        if company.account_config_id.account_fiscal_country_id != self.country_id:
            foreign_vat_fpos = self.env["account.fiscal.position"].search(
                [
                    *self.env["account.fiscal.position"]._check_company_domain(company),
                    ("foreign_vat", "!=", False),
                    ("country_id", "=", self.country_id.id),
                ],
                limit=1,
            )
            if foreign_vat_fpos:
                _debug.logic(
                    "vat_source",
                    report=self,
                    source="foreign_vat_fpos",
                    fiscal_position=foreign_vat_fpos,
                )
                return foreign_vat_fpos.foreign_vat

        if not company.vat and raise_warning:
            action = self.env.ref("base.action_res_company_form")
            raise RedirectWarning(
                _("No VAT number associated with your company. Please define one."),
                action.id,
                _("Company Settings"),
            )
        _debug.logic(
            "vat_source",
            report=self,
            source="company",
            company=company,
            missing=not company.vat,
        )
        return company.vat

    @_debug.perf.timed
    def action_download_xlsx_accounts_coverage_report(self):
        """Generate an XLSX file used to debug the report, issuing the following warnings when applicable:

        - an account exists in the Chart of Accounts but is not mentioned in any line of the report (red)
        - an account is reported in multiple lines of the report (orange)
        - an account is reported in a line of the report but does not exist in the Chart of Accounts (yellow)
        """
        _debug.lifecycle("action_download_xlsx_accounts_coverage_report", records=self)
        self.check_singleton()
        if not self.is_account_coverage_report_available:
            raise UserError(
                _("The Accounts Coverage Report is not available for this report.")
            )

        output = io.BytesIO()
        import xlsxwriter

        with xlsxwriter.Workbook(output, {"in_memory": True}) as workbook:
            worksheet = workbook.add_worksheet(_("Accounts coverage"))
            worksheet.set_column(0, 0, 20)
            worksheet.set_column(1, 1, 75)
            worksheet.set_column(2, 2, 80)
            worksheet.freeze_panes(1, 0)

            headers = [
                _("Account Code / Tag"),
                _("Error message"),
                _("Report lines mentioning the account code"),
                "#FFFFFF",
            ]
            lines = [headers] + self._generate_accounts_coverage_report_xlsx_lines()
            for i, line in enumerate(lines):
                worksheet.write_row(
                    i, 0, line[:-1], workbook.add_format({"bg_color": line[-1]})
                )

        attachment_id = self.env["ir.attachment"].create(
            {
                "name": f"{self.display_name} - {_('Accounts Coverage Report')}",
                "datas": base64.encodebytes(output.getvalue()),
            }
        )
        _debug.pipeline(
            "coverage_xlsx_written",
            report=self,
            rows=len(lines),
            attachment=attachment_id,
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "download",
        }

    @_debug.perf.timed
    def _generate_accounts_coverage_report_xlsx_lines(self):
        """Generate the lines of the accounts coverage XLSX file, issuing the following warnings when applicable:

        - an account exists in the Chart of Accounts but is not mentioned in any line of the report (red)
        - an account is reported in multiple lines of the report (orange)
        - an account is reported in a line of the report but does not exist in the Chart of Accounts (yellow)
        """

        def get_domain_account(prefix):
            # Helper function to get the right domain to find the account
            # This function verifies if we have to look for a tag or if we have
            # to look for an account code.
            if tag_matching := ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix):
                if tag_matching["ref"]:
                    account_tag_id = self.env["ir.model.data"]._xmlid_to_res_id(
                        tag_matching["ref"]
                    )
                else:
                    account_tag_id = int(tag_matching["id"])
                return "tag_ids", "in", (account_tag_id,)
            else:
                return "code", "=like", f"{prefix}%"

        self.check_singleton()

        AccountAccount = self.env["account.account"].with_context(active_test=False)
        all_reported_accounts = AccountAccount  # All accounts mentioned in the report (including those reported without using the account code)
        accounts_by_expressions = {}  # {expression_id: account.account objects}
        reported_account_codes = []  # [{'prefix': ..., 'balance': ..., 'exclude': ..., 'line': ...}, ...]
        non_existing_codes = defaultdict(
            lambda: self.env["account.report.line"]
        )  # {non_existing_account_code: {lines_with_that_code,}}
        lines_per_non_linked_tag = defaultdict(lambda: self.env["account.report.line"])
        lines_using_bad_operator_per_tag = defaultdict(
            lambda: self.env["account.report.line"]
        )
        candidate_duplicate_codes = defaultdict(
            lambda: self.env["account.report.line"]
        )  # {candidate_duplicate_account_code: {lines_with_that_code,}}
        duplicate_codes = defaultdict(
            lambda: self.env["account.report.line"]
        )  # {verified duplicate_account_code: {lines_with_that_code,}}
        duplicate_codes_same_line = defaultdict(
            lambda: self.env["account.report.line"]
        )  # {duplicate_account_code: {line_with_that_code_multiple_times,}}
        common_account_domain = [
            *AccountAccount._check_company_domain(self.env.company),
        ]

        # tag_ids already linked to an account - avoid several search_count to know if the tag is used or not
        tag_ids_linked_to_account = set(
            AccountAccount.search([("tag_ids", "!=", False)]).tag_ids.ids
        )

        expressions = self.line_ids.expression_ids._expand_aggregations()
        _debug.pipeline(
            "coverage_expressions_expanded",
            report=self,
            expressions=expressions,
            linked_tags=len(tag_ids_linked_to_account),
        )
        for i, expr in enumerate(expressions):
            reported_accounts = AccountAccount
            if expr.engine == "domain":
                domain = literal_eval(expr.formula.strip())

                # Rewrite the aml domain into an account one by mapping every
                # leaf in place and letting Domain recombine, so the nesting and
                # the arity stay correct by construction and a dropped term is a
                # TRUE substitution rather than list surgery. The hand-rolled
                # version popped the operator only when the skipped term followed
                # it directly, so `['&', ('account_id.code', ...), ('date', ...)]`
                # came out as a dangling operator with one operand, and a domain
                # opening on a non-account term popped from an empty list.
                def rewrite_condition(condition, expr=expr):
                    field_expr = condition.field_expr
                    if not field_expr.startswith("account_id."):
                        return Domain.TRUE
                    operand = [
                        field_expr.replace("account_id.", "", 1),
                        condition.operator,
                        condition.value,
                    ]
                    # Check that the code exists in the CoA
                    if operand[0] == "code" and not AccountAccount.search_count(
                        [operand], limit=1
                    ):
                        _debug.logic(
                            "coverage_code_missing", expression=expr, code=operand[2]
                        )
                        non_existing_codes[operand[2]] |= expr.report_line_id
                    elif operand[0] == "tag_ids":
                        tag_ids = operand[2]
                        if not isinstance(tag_ids, (list, tuple, set)):
                            tag_ids = [tag_ids]

                        if operand[1] in ("=", "in"):
                            tag_ids_to_browse = [
                                tag_id
                                for tag_id in tag_ids
                                if tag_id not in tag_ids_linked_to_account
                            ]
                            for tag in self.env["account.account.tag"].browse(
                                tag_ids_to_browse
                            ):
                                lines_per_non_linked_tag[f"{tag.name} ({tag.id})"] |= (
                                    expr.report_line_id
                                )
                        else:
                            _debug.logic(
                                "coverage_tag_bad_operator",
                                expression=expr,
                                operator=operand[1],
                                tags=len(tag_ids),
                            )
                            for tag in self.env["account.account.tag"].browse(tag_ids):
                                lines_using_bad_operator_per_tag[
                                    f"{tag.name} ({tag.id}) - Operator: {operand[1]}"
                                ] |= expr.report_line_id

                    return Domain(*operand)

                reported_accounts += AccountAccount.search(  # noqa: E8507 - a coverage audit: one query per expression, each with its own domain
                    Domain(domain).map_conditions(rewrite_condition)
                )
            elif expr.engine == "account_codes":
                account_codes = []
                for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(
                    expr.formula.replace(" ", "")
                ):
                    if not token:
                        continue
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                    if not token_match:
                        continue

                    parsed_token = token_match.groupdict()
                    account_codes.append(
                        {
                            "prefix": parsed_token["prefix"],
                            "balance": parsed_token["balance_character"],
                            "exclude": parsed_token["excluded_prefixes"].split(",")
                            if parsed_token["excluded_prefixes"]
                            else [],
                            "line": expr.report_line_id,
                        }
                    )

                for account_code in account_codes:
                    reported_account_codes.append(account_code)
                    exclude_domain_accounts = [
                        get_domain_account(exclude_code)
                        for exclude_code in account_code["exclude"]
                    ]
                    reported_accounts += AccountAccount.search(  # noqa: E8507 - a coverage audit: one query per account code, each with its own prefix and exclusions
                        [
                            *common_account_domain,
                            get_domain_account(account_code["prefix"]),
                            *[
                                excl_domain
                                for excl_tuple in exclude_domain_accounts
                                for excl_domain in ("!", excl_tuple)
                            ],
                        ]
                    )

                    # Check that the code exists in the CoA or that the tag is linked to an account
                    prefixes_to_check = [account_code["prefix"]] + account_code[
                        "exclude"
                    ]
                    for prefix_to_check in prefixes_to_check:
                        account_domain = get_domain_account(prefix_to_check)
                        if not AccountAccount.search_count(  # noqa: E8507 - a coverage audit: one existence probe per prefix
                            [
                                *common_account_domain,
                                account_domain,
                            ],
                            limit=1,
                        ):
                            # Identify if we're working with account codes or account tags
                            if account_domain[0] == "code":
                                non_existing_codes[prefix_to_check] |= account_code[
                                    "line"
                                ]
                            elif account_domain[0] == "tag_ids":
                                lines_per_non_linked_tag[prefix_to_check] |= (
                                    account_code["line"]
                                )

            all_reported_accounts |= reported_accounts
            accounts_by_expressions[expr.id] = reported_accounts

            # Check if an account is reported multiple times in the same line of the report
            if len(reported_accounts) != len(set(reported_accounts)):
                seen = set()
                for reported_account in reported_accounts:
                    if reported_account not in seen:
                        seen.add(reported_account)
                    else:
                        duplicate_codes_same_line[reported_account.code] |= (
                            expr.report_line_id
                        )

            # Check if the account is reported in multiple lines of the report
            for expr2 in expressions[: i + 1]:
                reported_accounts2 = accounts_by_expressions[expr2.id]
                for duplicate_account in reported_accounts & reported_accounts2:
                    if (
                        len(expr.report_line_id | expr2.report_line_id) > 1
                        and expr.date_scope == expr2.date_scope
                        and expr.subformula == expr2.subformula
                    ):
                        candidate_duplicate_codes[duplicate_account.code] |= (
                            expr.report_line_id | expr2.report_line_id
                        )

        _debug.pipeline(
            "coverage_expressions_scanned",
            report=self,
            reported_accounts=len(all_reported_accounts),
            account_code_terms=len(reported_account_codes),
            candidate_duplicates=len(candidate_duplicate_codes),
            same_line_duplicates=len(duplicate_codes_same_line),
            non_existing_codes=len(non_existing_codes),
            non_linked_tags=len(lines_per_non_linked_tag),
            bad_operator_tags=len(lines_using_bad_operator_per_tag),
        )
        # Check that the duplicates are not false positives because of the balance character
        for (
            candidate_duplicate_code,
            candidate_duplicate_lines,
        ) in candidate_duplicate_codes.items():
            if len(set(candidate_duplicate_lines.mapped("name"))) <= 1:
                continue
            seen_balance_chars = []
            seen_balance_chars.extend(
                reported_account_code["balance"]
                for reported_account_code in reported_account_codes
                if candidate_duplicate_code.startswith(reported_account_code["prefix"])
                and reported_account_code["balance"]
            )
            if (
                not seen_balance_chars
                or seen_balance_chars.count("C") > 1
                or seen_balance_chars.count("D") > 1
            ):
                duplicate_codes[candidate_duplicate_code] |= candidate_duplicate_lines

        _debug.logic(
            "coverage_duplicates_verified",
            report=self,
            candidates=len(candidate_duplicate_codes),
            verified=len(duplicate_codes),
        )
        # Check that all codes in CoA are correctly reported
        if self.root_report_id == self.env.ref("account.profit_and_loss"):
            accounts_in_coa = AccountAccount.search(
                [
                    *common_account_domain,
                    (
                        "account_type",
                        "in",
                        (
                            "income",
                            "income_other",
                            "expense",
                            "expense_depreciation",
                            "expense_direct_cost",
                        ),
                    ),
                    ("account_type", "!=", "off_balance"),
                ]
            )
            _debug.logic(
                "coverage_coa_scope",
                report=self,
                scope="profit_and_loss",
                coa_accounts=len(accounts_in_coa),
            )
        else:  # Balance Sheet
            accounts_in_coa = AccountAccount.search(
                [
                    *common_account_domain,
                    (
                        "account_type",
                        "not in",
                        (
                            "off_balance",
                            "income",
                            "income_other",
                            "expense",
                            "expense_depreciation",
                            "expense_direct_cost",
                        ),
                    ),
                ]
            )
            _debug.logic(
                "coverage_coa_scope",
                report=self,
                scope="balance_sheet",
                coa_accounts=len(accounts_in_coa),
            )

        # Compute codes that exist in the CoA but are not reported in the report.
        # account.account.code is computed per company and is False for an account
        # that has none in the active one; keeping those would put a bool in a set
        # of str and make the sort below raise.
        non_reported_codes = {
            code
            for code in (accounts_in_coa - all_reported_accounts).mapped("code")
            if code
        }

        # Create the lines that will be displayed in the xlsx
        all_reported_codes = sorted(
            {code for code in all_reported_accounts.mapped("code") if code}
            | non_reported_codes
            | non_existing_codes.keys()
        )
        _debug.pipeline(
            "coverage_codes_collected",
            report=self,
            codes=len(all_reported_codes),
            non_reported=len(non_reported_codes),
        )
        errors_trie = self._get_accounts_coverage_report_errors_trie(
            all_reported_codes,
            non_reported_codes,
            duplicate_codes,
            duplicate_codes_same_line,
            non_existing_codes,
        )
        errors_trie["children"].update(
            **self._get_account_tag_coverage_report_errors_trie(
                lines_per_non_linked_tag, lines_using_bad_operator_per_tag
            )
        )  # Add tags that are not linked to an account

        errors_trie = self._regroup_accounts_coverage_report_errors_trie(errors_trie)
        return self._get_accounts_coverage_report_coverage_lines("", errors_trie)

    @api.depends("country_id", "chart_template", "root_report_id")
    @_debug.perf.timed
    def _compute_is_account_coverage_report_available(self):
        for report in self:
            report.is_account_coverage_report_available = (
                (
                    report.availability_condition == "country"
                    and self.env.company.account_config_id.account_fiscal_country_id
                    == report.country_id
                )
                or (
                    report.availability_condition == "coa"
                    and self.env.company.account_config_id.chart_template
                    == report.chart_template
                )
                or report.availability_condition == "always"
            ) and report.root_report_id in (
                self.env.ref("account.profit_and_loss", raise_if_not_found=False),
                self.env.ref("account.balance_sheet", raise_if_not_found=False),
            )

    @_debug.perf.timed
    def _get_accounts_coverage_report_errors_trie(
        self,
        all_reported_codes,
        non_reported_codes,
        duplicate_codes,
        duplicate_codes_same_line,
        non_existing_codes,
    ):
        """Create the trie used to regroup the same errors on the same subcodes, in the form:

        {
            "children": {
                "1": {
                    "children": {
                        "10": { ... },
                        "11": { ... },
                    },
                    "lines": {
                        "Line1",
                        "Line2",
                    },
                    "errors": {
                        "DUPLICATE"
                    }
                },
            "lines": {
                "",
            },
            "errors": {
                None    # Avoid that all codes are merged into the root with the code "" in case all of the errors are the same
            },
        }
        """
        errors_trie = {"children": {}, "lines": {}, "errors": {None}}
        for reported_code in all_reported_codes:
            current_trie = errors_trie
            lines = self.env["account.report.line"]
            errors = set()
            if reported_code in non_reported_codes:
                errors.add("NON_REPORTED")
            elif reported_code in duplicate_codes_same_line:
                lines |= duplicate_codes_same_line[reported_code]
                errors.add("DUPLICATE_SAME_LINE")
            elif reported_code in duplicate_codes:
                lines |= duplicate_codes[reported_code]
                errors.add("DUPLICATE")
            elif reported_code in non_existing_codes:
                lines |= non_existing_codes[reported_code]
                errors.add("NON_EXISTING")
            else:
                errors.add("NONE")

            for j in range(1, len(reported_code) + 1):
                current_trie = current_trie["children"].setdefault(
                    reported_code[:j],
                    {"children": {}, "lines": lines, "errors": errors},
                )
        _debug.pipeline(
            "coverage_errors_trie_built",
            report=self,
            codes=len(all_reported_codes),
            roots=len(errors_trie["children"]),
        )
        return errors_trie

    @api.model
    def _get_account_tag_coverage_report_errors_trie(
        self, lines_per_non_linked_tag, lines_per_bad_operator_tag
    ):
        """As we don't want to make a hierarchy for tags, we use a specific
        function to handle tags.
        """
        errors = {
            non_linked_tag: {
                "children": {},
                "lines": line,
                "errors": {"NON_LINKED"},
            }
            for non_linked_tag, line in lines_per_non_linked_tag.items()
        }
        errors.update(
            {
                bad_operator_tag: {
                    "children": {},
                    "lines": line,
                    "errors": {"BAD_OPERATOR"},
                }
                for bad_operator_tag, line in lines_per_bad_operator_tag.items()
            }
        )
        return errors

    def _regroup_accounts_coverage_report_errors_trie(self, trie):
        """Regroup the codes sharing the same error under their common subcode/prefix, in place on the given trie."""
        if trie.get("children"):
            children_errors = set()
            children_lines = self.env["account.report.line"]
            if trie.get("errors"):  # Add own error
                children_errors |= set(trie.get("errors"))
            for child in trie["children"].values():
                regroup = self._regroup_accounts_coverage_report_errors_trie(child)
                children_lines |= regroup["lines"]
                children_errors |= set(regroup["errors"])
            if (
                len(children_errors) == 1
                and children_lines
                and children_lines == trie["lines"]
            ):
                trie["children"] = {}
                trie["lines"] = children_lines
                trie["errors"] = children_errors
        return trie

    @_debug.perf.timed
    def _get_accounts_coverage_report_coverage_lines(
        self, subcode, trie, coverage_lines=None
    ):
        """Create the coverage lines from the grouped trie. Each line has:

        - the account code
        - the error message
        - the lines on which the account code is used
        - the color of the error message for the xlsx
        """
        # Dictionnary of the three possible errors, their message and the corresponding color for the xlsx file
        ERRORS = {
            "NON_REPORTED": {
                "msg": _(
                    "This account exists in the Chart of Accounts but is not mentioned in any line of the report"
                ),
                "color": "#FF0000",
            },
            "DUPLICATE": {
                "msg": _("This account is reported in multiple lines of the report"),
                "color": "#FF8916",
            },
            "DUPLICATE_SAME_LINE": {
                "msg": _(
                    "This account is reported multiple times on the same line of the report"
                ),
                "color": "#E6A91D",
            },
            "NON_EXISTING": {
                "msg": _(
                    "This account is reported in a line of the report but does not exist in the Chart of Accounts"
                ),
                "color": "#FFBF00",
            },
            "NON_LINKED": {
                "msg": _(
                    "This tag is reported in a line of the report but is not linked to any account of the Chart of Accounts"
                ),
                "color": "#FFBF00",
            },
            "BAD_OPERATOR": {
                "msg": _("The used operator is not supported for this expression."),
                "color": "#FFBF00",
            },
        }
        if coverage_lines is None:
            coverage_lines = []
        if trie.get("children"):
            for child in trie.get("children"):
                self._get_accounts_coverage_report_coverage_lines(
                    child, trie["children"][child], coverage_lines
                )
        else:
            error = next(iter(trie["errors"])) if trie["errors"] else False
            if error and error != "NONE":
                coverage_lines.append(
                    [
                        subcode,
                        ERRORS[error]["msg"],
                        " + ".join(trie["lines"].sorted().mapped("name")),
                        ERRORS[error]["color"],
                    ]
                )
        if _debug.pipeline.enabled and not subcode:
            _debug.pipeline(
                "coverage_lines_built", report=self, lines=len(coverage_lines)
            )
        return coverage_lines

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
            sections_source = self.env["account.report"].browse(sections_source_id)
        else:
            sections_source = self

        _debug.logic(
            "filename_from_sections",
            report=self,
            sections_source=sections_source,
            extension=extension,
        )
        return f"{sections_source.name.lower().replace(' ', '_')}_{_transform_period(period)}{_get_company_name(options['companies'])}.{extension}"

    def _get_layout_footer(self, rcontext):
        if self.env.context.get("exclude_page_footer"):
            return None
        else:
            footer_html = self.env["ir.actions.report"]._render_template(
                "account.internal_layout", values=rcontext
            )
            footer_html = self.env["ir.actions.report"]._render_template(
                "web.minimal_layout",
                values=dict(
                    rcontext, subst=True, body=markupsafe.Markup(footer_html.decode())
                ),
            )
            return footer_html.decode()

    @_debug.perf.timed
    def _generate_file_data_with_error_check(
        self, options, content_generator, generator_params, errors
    ):
        """Checks for critical errors (i.e. errors that would cause the rendering to fail) in the generator values.
        If at least one error is critical, the 'account.report.file.download.error.wizard' wizard is opened
        before rendering the file, so they can be fixed.
        If there are only non-critical errors, the wizard is opened after the file has been generated,
        allowing the user to download it anyway.

        :param dict options: The report options.
        :param def content_generator: The function used to generate the exported content.
        :param dict generator_params: The parameters passed to the 'content_generator' method (List).
        :param dict errors: A dict of errors in the following format:
            {
                key: {
                    'message': The error message to be displayed in the wizard (String),
                    'action_text': The text of the action button (String),
                    'action': Contains the action values (Dictionary),
                    'level': One of 'info', 'warning', 'danger'. (String).
                             Only the 'danger' level represents a blocking error.
                },
                key: {...},
            }
        :returns: The data that will be used by the file generator.
        :rtype: dict
        """
        if errors is None:
            errors = []
        self.check_singleton()
        if any(error_value.get("level") == "danger" for error_value in errors.values()):
            _debug.logic("file_generation_blocked", report=self, errors=len(errors))
            raise AccountReportFileDownloadException(errors)

        content = content_generator(**generator_params)

        file_data = {
            "file_name": self.get_default_report_filename(
                options, generator_params["file_type"]
            ),
            "file_content": re.sub(r"\n\s*\n", "\n", content).encode(),
            "file_type": generator_params["file_type"],
        }

        _debug.pipeline(
            "file_data_generated",
            report=self,
            file_type=generator_params["file_type"],
            size=len(file_data["file_content"]),
            non_blocking_errors=len(errors),
        )
        if errors:
            raise AccountReportFileDownloadException(errors, file_data)

        return file_data
