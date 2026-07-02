# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import io

from werkzeug.exceptions import BadRequest, Forbidden

from odoo import fields, http
from odoo.http import request
from odoo.http.stream import content_disposition

_CSV_INJECTION_CHARS = frozenset("=+@\t\r\n")


class L10nPhPosLineVoidController(http.Controller):
    _DEFAULT_EXPORT_LIMIT = 10000
    _MAX_EXPORT_LIMIT = 50000
    _CSV_COLUMNS = [
        ("transaction_date", "Transaction Date & Timestamp"),
        ("logged_at", "Log Date & Timestamp"),
        ("approver_badge_number", "Approver RFID / Badge #"),
        ("approver_employee_id", "Approver Name"),
        ("cashier_badge_number", "Cashier RFID / Badge #"),
        ("cashier_employee_id", "Cashier Name"),
        ("config_id", "POS / Machine Name"),
        ("reason", "Reason"),
        ("remark", "Remark"),
        ("product_id", "Product"),
        ("description", "Description"),
        ("quantity", "Quantity"),
        ("unit_price", "Unit Price"),
        ("net_amount", "Net Amount"),
    ]

    @http.route(
        "/l10n_ph_pos/line_voids/export.csv",
        type="http",
        auth="user",
        methods=["GET"],
        readonly=True,
    )
    def export_line_voids(self, **kwargs):
        if not request.env.user.has_group("point_of_sale.group_pos_manager"):
            raise Forbidden()

        void_model = request.env["l10n_ph.pos.line.void"]
        void_model.check_access("read")

        domain = [("company_id", "in", request.env.companies.ids)]
        from_date = self._parse_datetime_param(kwargs.get("from_date"), "from_date")
        to_date = self._parse_datetime_param(kwargs.get("to_date"), "to_date")
        config_id = self._parse_int_param(kwargs.get("config_id"), "config_id")
        employee_id = self._parse_int_param(kwargs.get("employee_id"), "employee_id")
        limit = (
            self._parse_int_param(kwargs.get("limit"), "limit")
            or self._DEFAULT_EXPORT_LIMIT
        )
        if limit > self._MAX_EXPORT_LIMIT:
            raise BadRequest(
                f"Parameter `limit` cannot exceed {self._MAX_EXPORT_LIMIT}.",
            )

        if from_date and to_date and from_date > to_date:
            msg = "Parameter `from_date` must be before `to_date`."
            raise BadRequest(msg)

        if from_date:
            domain.append(("transaction_date", ">=", from_date))
        if to_date:
            domain.append(("transaction_date", "<=", to_date))
        if config_id:
            domain.append(("config_id", "=", config_id))
        if employee_id:
            domain.append(("approver_employee_id", "=", employee_id))

        records = void_model.search(
            domain,
            order="logged_at desc, id desc",
            limit=limit,
        )

        with io.StringIO() as buf:
            writer = csv.writer(buf)
            writer.writerow([label for _, label in self._CSV_COLUMNS])
            for record in records:
                writer.writerow(self._format_csv_row(record))
            data = buf.getvalue()

        return request.make_response(
            data,
            headers=[
                ("Content-Type", "text/csv; charset=utf-8"),
                (
                    "Content-Disposition",
                    content_disposition("line_void_transactions.csv"),
                ),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )

    def _format_csv_row(self, record):
        """Format a single audit record as a CSV row."""
        row = []
        for field_name, _ in self._CSV_COLUMNS:
            value = record[field_name]
            if hasattr(value, "display_name"):
                value = value.display_name or ""
            elif not value and value != 0:
                value = ""
            row.append(self._sanitize_csv_cell(value))
        return row

    def _parse_int_param(self, value, param_name):
        if not value:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise BadRequest(f"Parameter `{param_name}` must be an integer.") from exc
        if parsed <= 0:
            raise BadRequest(f"Parameter `{param_name}` must be a positive integer.")
        return parsed

    def _parse_datetime_param(self, value, param_name):
        if not value:
            return None
        try:
            return fields.Datetime.to_string(fields.Datetime.to_datetime(value))
        except (TypeError, ValueError) as exc:
            raise BadRequest(
                f"Parameter `{param_name}` must be a valid date/datetime.",
            ) from exc

    @staticmethod
    def _sanitize_csv_cell(value):
        """Prevent CSV formula injection for string values."""
        if not isinstance(value, str):
            return value
        if not value:
            return value
        if value[0] in _CSV_INJECTION_CHARS:
            return f"'{value}"
        if value[0] == "-" and not value.lstrip("-").replace(".", "", 1).isdigit():
            return f"'{value}"
        return value
