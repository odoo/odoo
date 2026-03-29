# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AbstractReportXslx(models.AbstractModel):
    _name = "report.account_financial_report.abstract_report_xlsx"
    _description = "Abstract XLSX Account Financial Report"
    _inherit = "report.report_xlsx.abstract"

    def get_workbook_options(self):
        vals = super().get_workbook_options()
        vals.update({"constant_memory": True})
        return vals

    def generate_xlsx_report(self, workbook, data, objects):
        # Initialize report variables
        report_data = {
            "workbook": None,
            "sheet": None,  # main sheet which will contains report
            "columns": None,  # columns of the report
            "row_pos": None,  # row_pos must be incremented at each writing lines
            "formats": None,
        }
        self._define_formats(workbook, report_data)
        # Get report data
        report_name = self._get_report_name(objects, data=data)
        report_footer = self._get_report_footer()
        filters = self._get_report_filters(objects)
        report_data["columns"] = self._get_report_columns(objects)
        report_data["workbook"] = workbook
        report_data["sheet"] = workbook.add_worksheet(report_name[:31])
        self._set_column_width(report_data)
        # Fill report
        report_data["row_pos"] = 0
        self._write_report_title(report_name, report_data)
        self._write_filters(filters, report_data)
        self._generate_report_content(workbook, objects, data, report_data)
        self._write_report_footer(report_footer, report_data)

    def _define_formats(self, workbook, report_data):
        """Add cell formats to current workbook.
        Those formats can be used on all cell.
        Available formats are :
         * format_bold
         * format_right
         * format_right_bold_italic
         * format_header_left
         * format_header_center
         * format_header_right
         * format_header_amount
         * format_amount
         * format_percent_bold_italic
        """
        currency_id = self.env["res.company"]._default_currency_id()
        report_data["formats"] = {
            "format_bold": workbook.add_format({"bold": True}),
            "format_right": workbook.add_format({"align": "right"}),
            "format_left": workbook.add_format({"align": "left"}),
            "format_right_bold_italic": workbook.add_format(
                {"align": "right", "bold": True, "italic": True}
            ),
            "format_header_left": workbook.add_format(
                {"bold": True, "border": True, "bg_color": "#FFFFCC"}
            ),
            "format_header_center": workbook.add_format(
                {"bold": True, "align": "center", "border": True, "bg_color": "#FFFFCC"}
            ),
            "format_header_right": workbook.add_format(
                {"bold": True, "align": "right", "border": True, "bg_color": "#FFFFCC"}
            ),
            "format_header_amount": workbook.add_format(
                {"bold": True, "border": True, "bg_color": "#FFFFCC"}
            ),
            "format_amount": workbook.add_format(),
            "format_amount_bold": workbook.add_format({"bold": True}),
            "format_percent_bold_italic": workbook.add_format(
                {"bold": True, "italic": True}
            ),
        }
        report_data["formats"]["format_amount"].set_num_format(
            "#,##0." + "0" * currency_id.decimal_places
        )
        report_data["formats"]["format_header_amount"].set_num_format(
            "#,##0." + "0" * currency_id.decimal_places
        )
        report_data["formats"]["format_percent_bold_italic"].set_num_format("#,##0.00%")
        report_data["formats"]["format_amount_bold"].set_num_format(
            "#,##0." + "0" * currency_id.decimal_places
        )

    def _set_column_width(self, report_data):
        """Set width for all defined columns.
        Columns are defined with `_get_report_columns` method.
        """
        for position, column in report_data["columns"].items():
            report_data["sheet"].set_column(position, position, column["width"])

    def _write_report_title(self, title, report_data):
        """Write report title on current line using all defined columns width.
        Columns are defined with `_get_report_columns` method.
        """
        report_data["sheet"].merge_range(
            report_data["row_pos"],
            0,
            report_data["row_pos"],
            len(report_data["columns"]) - 1,
            title,
            report_data["formats"]["format_bold"],
        )
        report_data["row_pos"] += 3

    def _write_report_footer(self, footer, report_data):
        """Write report footer .
        Columns are defined with `_get_report_columns` method.
        """
        if footer:
            report_data["row_pos"] += 1
            report_data["sheet"].merge_range(
                report_data["row_pos"],
                0,
                report_data["row_pos"],
                len(report_data["columns"]) - 1,
                footer,
                report_data["formats"]["format_left"],
            )
            report_data["row_pos"] += 1

    def _write_filters(self, filters, report_data):
        """Write one line per filters on starting on current line.
        Columns number for filter name is defined
        with `_get_col_count_filter_name` method.
        Columns number for filter value is define
        with `_get_col_count_filter_value` method.
        """
        col_name = 1
        col_count_filter_name = self._get_col_count_filter_name()
        col_count_filter_value = self._get_col_count_filter_value()
        col_value = col_name + col_count_filter_name + 1
        for title, value in filters:
            report_data["sheet"].merge_range(
                report_data["row_pos"],
                col_name,
                report_data["row_pos"],
                col_name + col_count_filter_name - 1,
                title,
                report_data["formats"]["format_header_left"],
            )
            report_data["sheet"].merge_range(
                report_data["row_pos"],
                col_value,
                report_data["row_pos"],
                col_value + col_count_filter_value - 1,
                value,
            )
            report_data["row_pos"] += 1
        report_data["row_pos"] += 2

    def write_array_title(self, title, report_data):
        """Write array title on current line using all defined columns width.
        Columns are defined with `_get_report_columns` method.
        """
        report_data["sheet"].merge_range(
            report_data["row_pos"],
            0,
            report_data["row_pos"],
            len(report_data["columns"]) - 1,
            title,
            report_data["formats"]["format_bold"],
        )
        report_data["row_pos"] += 1

    def write_array_header(self, report_data):
        """Write array header on current line using all defined columns name.
        Columns are defined with `_get_report_columns` method.
        """
        for col_pos, column in report_data["columns"].items():
            report_data["sheet"].write(
                report_data["row_pos"],
                col_pos,
                column["header"],
                report_data["formats"]["format_header_center"],
            )
        report_data["row_pos"] += 1

    def write_line(self, line_object, report_data):
        """Write a line on current line using all defined columns field name.
        Columns are defined with `_get_report_columns` method.
        """
        for col_pos, column in report_data["columns"].items():
            value = getattr(line_object, column["field"])
            cell_type = column.get("type", "string")
            if cell_type == "many2one":
                report_data["sheet"].write_string(
                    report_data["row_pos"],
                    col_pos,
                    value.name or "",
                    report_data["formats"]["format_right"],
                )
            elif cell_type == "string":
                if (
                    hasattr(line_object, "account_group_id")
                    and line_object.account_group_id
                ):
                    report_data["sheet"].write_string(
                        report_data["row_pos"],
                        col_pos,
                        value or "",
                        report_data["formats"]["format_bold"],
                    )
                else:
                    report_data["sheet"].write_string(
                        report_data["row_pos"], col_pos, value or ""
                    )
            elif cell_type == "amount":
                if (
                    hasattr(line_object, "account_group_id")
                    and line_object.account_group_id
                ):
                    cell_format = report_data["formats"]["format_amount_bold"]
                else:
                    cell_format = report_data["formats"]["format_amount"]
                report_data["sheet"].write_number(
                    report_data["row_pos"], col_pos, float(value), cell_format
                )
            elif cell_type == "amount_currency":
                if line_object.currency_id:
                    format_amt = self._get_currency_amt_format(line_object, report_data)
                    report_data["sheet"].write_number(
                        report_data["row_pos"], col_pos, float(value), format_amt
                    )
        report_data["row_pos"] += 1

    def write_line_from_dict(self, line_dict, report_data):
        """Write a line on current line"""
        for col_pos, column in report_data["columns"].items():
            value = line_dict.get(column["field"], False)
            cell_type = column.get("type", "string")
            if cell_type == "string":
                if line_dict.get("type", "") == "group_type":
                    report_data["sheet"].write_string(
                        report_data["row_pos"],
                        col_pos,
                        value or "",
                        report_data["formats"]["format_bold"],
                    )
                else:
                    if (
                        not isinstance(value, str)
                        and not isinstance(value, bool)
                        and not isinstance(value, int)
                    ):
                        value = value and value.strftime("%d/%m/%Y")
                    report_data["sheet"].write_string(
                        report_data["row_pos"], col_pos, value or ""
                    )
            elif cell_type == "amount":
                if (
                    line_dict.get("account_group_id", False)
                    and line_dict["account_group_id"]
                ):
                    cell_format = report_data["formats"]["format_amount_bold"]
                else:
                    cell_format = report_data["formats"]["format_amount"]
                report_data["sheet"].write_number(
                    report_data["row_pos"], col_pos, float(value), cell_format
                )
            elif cell_type == "amount_currency":
                if line_dict.get("currency_name", False):
                    format_amt = self._get_currency_amt_format_dict(
                        line_dict, report_data
                    )
                    report_data["sheet"].write_number(
                        report_data["row_pos"], col_pos, float(value), format_amt
                    )
            elif cell_type == "currency_name":
                report_data["sheet"].write_string(
                    report_data["row_pos"],
                    col_pos,
                    value or "",
                    report_data["formats"]["format_right"],
                )
            else:
                self.write_non_standard_column(cell_type, col_pos, value)
        report_data["row_pos"] += 1

    def write_initial_balance(self, my_object, label, report_data):
        """Write a specific initial balance line on current line
        using defined columns field_initial_balance name.
        Columns are defined with `_get_report_columns` method.
        """
        col_pos_label = self._get_col_pos_initial_balance_label()
        report_data["sheet"].write(
            report_data["row_pos"],
            col_pos_label,
            label,
            report_data["formats"]["format_right"],
        )
        for col_pos, column in report_data["columns"].items():
            if column.get("field_initial_balance"):
                value = getattr(my_object, column["field_initial_balance"])
                cell_type = column.get("type", "string")
                if cell_type == "string":
                    report_data["sheet"].write_string(
                        report_data["row_pos"], col_pos, value or ""
                    )
                elif cell_type == "amount":
                    report_data["sheet"].write_number(
                        report_data["row_pos"],
                        col_pos,
                        float(value),
                        report_data["formats"]["format_amount"],
                    )
                elif cell_type == "amount_currency":
                    if my_object.currency_id:
                        format_amt = self._get_currency_amt_format(
                            my_object, report_data
                        )
                        report_data["sheet"].write_number(
                            report_data["row_pos"], col_pos, float(value), format_amt
                        )
            elif column.get("field_currency_balance"):
                value = getattr(my_object, column["field_currency_balance"])
                cell_type = column.get("type", "string")
                if cell_type == "many2one":
                    if my_object.currency_id:
                        report_data["sheet"].write_string(
                            report_data["row_pos"],
                            col_pos,
                            value.name or "",
                            report_data["formats"]["format_right"],
                        )
        report_data["row_pos"] += 1

    def write_initial_balance_from_dict(self, my_object, label, report_data):
        """Write a specific initial balance line on current line
        using defined columns field_initial_balance name.
        Columns are defined with `_get_report_columns` method.
        """
        col_pos_label = self._get_col_pos_initial_balance_label()
        report_data["sheet"].write(
            report_data["row_pos"],
            col_pos_label,
            label,
            report_data["formats"]["format_right"],
        )
        for col_pos, column in report_data["columns"].items():
            if column.get("field_initial_balance"):
                value = my_object.get(column["field_initial_balance"], False)
                cell_type = column.get("type", "string")
                if cell_type == "string":
                    report_data["sheet"].write_string(
                        report_data["row_pos"], col_pos, value or ""
                    )
                elif cell_type == "amount":
                    report_data["sheet"].write_number(
                        report_data["row_pos"],
                        col_pos,
                        float(value),
                        report_data["formats"]["format_amount"],
                    )
                elif cell_type == "amount_currency":
                    if my_object["currency_id"]:
                        format_amt = self._get_currency_amt_format(
                            my_object, report_data
                        )
                        report_data["sheet"].write_number(
                            report_data["row_pos"], col_pos, float(value), format_amt
                        )
            elif column.get("field_currency_balance"):
                value = my_object.get(column["field_currency_balance"], False)
                cell_type = column.get("type", "string")
                if cell_type == "many2one":
                    if my_object["currency_id"]:
                        report_data["sheet"].write_string(
                            report_data["row_pos"],
                            col_pos,
                            value.name or "",
                            report_data["formats"]["format_right"],
                        )
        report_data["row_pos"] += 1

    def write_ending_balance(self, my_object, name, label, report_data):
        """Write a specific ending balance line on current line
        using defined columns field_final_balance name.
        Columns are defined with `_get_report_columns` method.
        """
        for i in range(0, len(report_data["columns"])):
            report_data["sheet"].write(
                report_data["row_pos"],
                i,
                "",
                report_data["formats"]["format_header_right"],
            )
        row_count_name = self._get_col_count_final_balance_name()
        col_pos_label = self._get_col_pos_final_balance_label()
        report_data["sheet"].merge_range(
            report_data["row_pos"],
            0,
            report_data["row_pos"],
            row_count_name - 1,
            name,
            report_data["formats"]["format_header_left"],
        )
        report_data["sheet"].write(
            report_data["row_pos"],
            col_pos_label,
            label,
            report_data["formats"]["format_header_right"],
        )
        for col_pos, column in report_data["columns"].items():
            if column.get("field_final_balance"):
                value = getattr(my_object, column["field_final_balance"])
                cell_type = column.get("type", "string")
                if cell_type == "string":
                    report_data["sheet"].write_string(
                        report_data["row_pos"],
                        col_pos,
                        value or "",
                        report_data["formats"]["format_header_right"],
                    )
                elif cell_type == "amount":
                    report_data["sheet"].write_number(
                        report_data["row_pos"],
                        col_pos,
                        float(value),
                        report_data["formats"]["format_header_amount"],
                    )
                elif cell_type == "amount_currency":
                    if my_object.currency_id:
                        format_amt = self._get_currency_amt_header_format(
                            my_object, report_data
                        )
                        report_data["sheet"].write_number(
                            report_data["row_pos"], col_pos, float(value), format_amt
                        )
            elif column.get("field_currency_balance"):
                value = getattr(my_object, column["field_currency_balance"])
                cell_type = column.get("type", "string")
                if cell_type == "many2one":
                    if my_object.currency_id:
                        report_data["sheet"].write_string(
                            report_data["row_pos"],
                            col_pos,
                            value.name or "",
                            report_data["formats"]["format_header_right"],
                        )
        report_data["row_pos"] += 1

    def write_ending_balance_from_dict(self, my_object, name, label, report_data):
        """Write a specific ending balance line on current line
        using defined columns field_final_balance name.
        Columns are defined with `_get_report_columns` method.
        """
        for i in range(0, len(report_data["columns"])):
            report_data["sheet"].write(
                report_data["row_pos"],
                i,
                "",
                report_data["formats"]["format_header_right"],
            )
        row_count_name = self._get_col_count_final_balance_name()
        col_pos_label = self._get_col_pos_final_balance_label()
        report_data["sheet"].merge_range(
            report_data["row_pos"],
            0,
            report_data["row_pos"],
            row_count_name - 1,
            name,
            report_data["formats"]["format_header_left"],
        )
        report_data["sheet"].write(
            report_data["row_pos"],
            col_pos_label,
            label,
            report_data["formats"]["format_header_right"],
        )
        for col_pos, column in report_data["columns"].items():
            if column.get("field_final_balance"):
                value = my_object.get(column["field_final_balance"], False)
                cell_type = column.get("type", "string")
                if cell_type == "string":
                    report_data["sheet"].write_string(
                        report_data["row_pos"],
                        col_pos,
                        value or "",
                        report_data["formats"]["format_header_right"],
                    )
                elif cell_type == "amount":
                    report_data["sheet"].write_number(
                        report_data["row_pos"],
                        col_pos,
                        float(value),
                        report_data["formats"]["format_header_amount"],
                    )
                elif cell_type == "amount_currency":
                    if my_object["currency_id"]:
                        format_amt = self._get_currency_amt_format_dict(
                            my_object, report_data
                        )
                        report_data["sheet"].write_number(
                            report_data["row_pos"], col_pos, float(value), format_amt
                        )
            elif column.get("field_currency_balance"):
                value = my_object.get(column["field_currency_balance"], False)
                cell_type = column.get("type", "string")
                if cell_type == "many2one":
                    if my_object["currency_id"]:
                        report_data["sheet"].write_string(
                            report_data["row_pos"],
                            col_pos,
                            value or "",
                            report_data["formats"]["format_header_right"],
                        )
                elif cell_type == "currency_name":
                    report_data["sheet"].write_string(
                        report_data["row_pos"],
                        col_pos,
                        value or "",
                        report_data["formats"]["format_header_right"],
                    )
        report_data["row_pos"] += 1

    def _get_currency_amt_format(self, line_object, report_data):
        """Return amount format specific for each currency."""
        if "account_group_id" in line_object and line_object["account_group_id"]:
            format_amt = report_data["formats"]["format_amount_bold"]
            field_prefix = "format_amount_bold"
        else:
            format_amt = report_data["formats"]["format_amount"]
            field_prefix = "format_amount"
        if "currency_id" in line_object and line_object.get("currency_id", False):
            if isinstance(line_object["currency_id"], int):
                currency = self.env["res.currency"].browse(line_object["currency_id"])
            else:
                currency = line_object["currency_id"]
            field_name = f"{field_prefix}_{currency.name}"
            if hasattr(self, field_name):
                format_amt = getattr(self, field_name)
            else:
                format_amt = report_data["workbook"].add_format()
                report_data["field_name"] = format_amt
                format_amt.set_num_format(self._report_xlsx_currency_format(currency))
        return format_amt

    def _get_currency_amt_format_dict(self, line_dict, report_data):
        """Return amount format specific for each currency."""
        if line_dict.get("account_group_id", False) and line_dict["account_group_id"]:
            format_amt = report_data["formats"]["format_amount_bold"]
            field_prefix = "format_amount_bold"
        else:
            format_amt = report_data["formats"]["format_amount"]
            field_prefix = "format_amount"
        if line_dict.get("currency_id", False) and line_dict["currency_id"]:
            if isinstance(line_dict["currency_id"], int):
                currency = self.env["res.currency"].browse(line_dict["currency_id"])
            else:
                currency = line_dict["currency_id"]
            field_name = f"{field_prefix}_{currency.name}"
            if hasattr(self, field_name):
                format_amt = getattr(self, field_name)
            else:
                format_amt = report_data["workbook"].add_format()
                report_data["field_name"] = format_amt
                format_amt.set_num_format(self._report_xlsx_currency_format(currency))
        return format_amt

    def _get_currency_amt_header_format(self, line_object, report_data):
        """Return amount header format for each currency."""
        format_amt = report_data["formats"]["format_header_amount"]
        if line_object.currency_id:
            field_name = f"format_header_amount_{line_object.currency_id.name}"
            if hasattr(self, field_name):
                format_amt = getattr(self, field_name)
            else:
                format_amt = report_data["workbook"].add_format(
                    {"bold": True, "border": True, "bg_color": "#FFFFCC"}
                )
                report_data["field_name"] = format_amt
                format_amount = "#,##0." + (
                    "0" * line_object.currency_id.decimal_places
                )
                format_amt.set_num_format(format_amount)
        return format_amt

    def _get_currency_amt_header_format_dict(self, line_object, report_data):
        """Return amount header format for each currency."""
        format_amt = report_data["formats"]["format_header_amount"]
        if line_object["currency_id"]:
            field_name = f"format_header_amount_{line_object['currency_name']}"
            if hasattr(self, field_name):
                format_amt = getattr(self, field_name)
            else:
                format_amt = report_data["workbook"].add_format(
                    {"bold": True, "border": True, "bg_color": "#FFFFCC"}
                )
                report_data["field_name"] = format_amt
                currency = self.env["res.currency"].browse(line_object["currency_id"])
                format_amount = "#,##0." + ("0" * currency.decimal_places)
                format_amt.set_num_format(format_amount)
        return format_amt

    def _generate_report_content(self, workbook, report, data, report_data):
        """
        Allow to fetch report content to be displayed.
        """
        raise NotImplementedError()

    def _get_report_complete_name(self, report, prefix, data=None):
        if report.company_id:
            suffix = (
                f" - {report.company_id.name} - {report.company_id.currency_id.name}"
            )
            return prefix + suffix
        return prefix

    def _get_report_name(self, report, data=False):
        """
        Allow to define the report name.
        Report name will be used as sheet name and as report title.
        :return: the report name
        """
        raise NotImplementedError()

    def _get_report_footer(self):
        """
        Allow to define the report footer.
        :return: the report footer
        """
        return False

    def _get_report_columns(self, report):
        """
        Allow to define the report columns
        which will be used to generate report.
        :return: the report columns as dict
        :Example:
        {
            0: {'header': 'Simple column',
                'field': 'field_name_on_my_object',
                'width': 11},
            1: {'header': 'Amount column',
                 'field': 'field_name_on_my_object',
                 'type': 'amount',
                 'width': 14},
        }
        """
        raise NotImplementedError()

    def _get_report_filters(self, report):
        """
        :return: the report filters as list
        :Example:
        [
            ['first_filter_name', 'first_filter_value'],
            ['second_filter_name', 'second_filter_value']
        ]
        """
        raise NotImplementedError()

    def _get_col_count_filter_name(self):
        """
        :return: the columns number used for filter names.
        """
        raise NotImplementedError()

    def _get_col_count_filter_value(self):
        """
        :return: the columns number used for filter values.
        """
        raise NotImplementedError()

    def _get_col_pos_initial_balance_label(self):
        """
        :return: the columns position used for initial balance label.
        """
        raise NotImplementedError()

    def _get_col_count_final_balance_name(self):
        """
        :return: the columns number used for final balance name.
        """
        raise NotImplementedError()

    def _get_col_pos_final_balance_label(self):
        """
        :return: the columns position used for final balance label.
        """
        raise NotImplementedError()

    def write_non_standard_column(self, cell_type, col_pos, value):
        """
        Write columns out of the columns type defined here.
        """
        raise NotImplementedError()
