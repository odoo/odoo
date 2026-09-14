import datetime
import functools
import io
import itertools
import logging
from collections.abc import Callable, Iterable, Iterator
from types import TracebackType
from typing import Any, Self

import xlsxwriter

from odoo.exceptions import UserError
from odoo.http import request
from odoo.libs.documents import ROWS, BaseWriter, mimetype_for, register_writer

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)

XLSX_MIMETYPE = mimetype_for("xlsx")


def none_values_filtered[T](
    func: Callable[[Iterable[T]], T | None],
) -> Callable[[Iterable[T | None]], T | None]:
    @functools.wraps(func)
    def wrap(iterable: Iterable[T | None]) -> T | None:
        return func(v for v in iterable if v is not None)

    return wrap


def allow_empty_iterable[T](
    func: Callable[[Iterable[T]], T],
) -> Callable[[Iterable[T]], T | None]:
    @functools.wraps(func)
    def wrap(iterable: Iterable[T]) -> T | None:
        iterator = iter(iterable)
        try:
            value = next(iterator)
            return func(itertools.chain([value], iterator))
        except StopIteration:
            return None

    return wrap


OPERATOR_MAPPING = {
    "max": none_values_filtered(allow_empty_iterable(max)),
    "min": none_values_filtered(allow_empty_iterable(min)),
    "sum": sum,
    "bool_and": all,
    "bool_or": any,
}


class GroupsTreeNode:
    def __init__(
        self,
        model: Any,
        fields: list[str],
        groupby: list[str],
        groupby_type: list[str],
    ) -> None:
        self._model = model
        self._export_field_names = fields
        self._groupby = groupby
        self._groupby_type = groupby_type

        self.count: int = 0
        self.children: dict[Any, GroupsTreeNode] = {}
        self.data: list[list[Any]] = []

    def _get_aggregate(
        self, field_name: str, data: Iterator[Any], aggregator: str
    ) -> Any:
        data = (value for value in data if value != "")

        if aggregator == "avg":
            return self._get_avg_aggregate(field_name, data)

        aggregate_func = OPERATOR_MAPPING.get(aggregator)
        if not aggregate_func:
            dbg.logic.debug(
                "[groups:%s] %s: aggregator %r unsupported",
                self._model._name,
                field_name,
                aggregator,
            )
            _logger.warning(
                "Unsupported export of aggregator '%s' for field %s on model %s",
                aggregator,
                field_name,
                self._model._name,
            )
            return None

        if self.data:
            return aggregate_func(data)
        return aggregate_func(
            child.aggregated_values.get(field_name) for child in self.children.values()
        )

    def _get_avg_aggregate(self, field_name: str, data: Iterator[Any]) -> float | None:
        if not self.count:
            return None
        aggregate_func = OPERATOR_MAPPING.get("sum")
        if self.data:
            return aggregate_func(data) / self.count
        children_sums = (
            (child.aggregated_values.get(field_name) or 0) * child.count
            for child in self.children.values()
        )
        return aggregate_func(children_sums) / self.count

    def _get_aggregated_field_names(self) -> list[str]:
        aggregated_field_names = []
        for field_name in self._export_field_names:
            if field_name == ".id":
                field_name = "id"
            if "/" in field_name or field_name not in self._model:
                continue
            field = self._model._fields[field_name]
            if field.aggregator:
                aggregated_field_names.append(field_name)
        return aggregated_field_names

    @functools.cached_property
    def aggregated_values(self) -> dict[str, Any]:
        aggregated_values = {}

        columns = list(zip(*self.data, strict=True))
        aggregated_field_names = self._get_aggregated_field_names()
        dbg.performance.debug(
            "[groups:%s] aggregate %s node: %d rows, %d children, %d aggregated fields",
            self._model._name,
            "leaf" if self.data else "inner",
            len(self.data),
            len(self.children),
            len(aggregated_field_names),
        )
        for index, field_name in enumerate(self._export_field_names):
            if field_name not in aggregated_field_names:
                continue
            field = self._model._fields[field_name]
            aggregated_values[field_name] = self._get_aggregate(
                field_name, iter(columns[index] if columns else ()), field.aggregator
            )

        return aggregated_values

    def child(self, key: Any) -> GroupsTreeNode:
        if key not in self.children:
            self.children[key] = GroupsTreeNode(
                self._model,
                self._export_field_names,
                self._groupby,
                self._groupby_type,
            )
        return self.children[key]

    def add_leaf(self, group: dict[str, Any], data: list[list[Any]]) -> None:
        leaf_path = [group.get(groupby_field) for groupby_field in self._groupby]
        count = group["__count"]

        node = self
        node.count += count
        for node_key in leaf_path:
            node = node.child(node_key)
            node.count += count

        if node.data:
            dbg.logic.debug(
                "[groups:%s] leaf %s already has %d rows, overwritten with %d",
                self._model._name,
                leaf_path,
                len(node.data),
                len(data),
            )
        node.data = data


class ExportXlsxWriter:
    def __init__(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        row_count: int,
        env: Any = None,
    ) -> None:
        self.env = request.env if env is None else env
        self.fields = fields
        self.columns_headers = columns_headers
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(
            self.output,
            {"in_memory": True, "constant_memory": True, "strings_to_formulas": False},
        )
        self.worksheet = self.workbook.add_worksheet()
        if row_count + 1 > self.worksheet.xls_rowmax:
            dbg.logic.debug(
                "[xlsx] %d rows exceed xls_rowmax %d, refused",
                row_count,
                self.worksheet.xls_rowmax,
            )
            raise UserError(
                self.env._(
                    "There are too many rows (%(count)s rows, limit: %(limit)s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.",
                    count=row_count,
                    limit=self.worksheet.xls_rowmax,
                )
            )
        self.header_style = self.workbook.add_format({"bold": True})
        self.date_style = self.workbook.add_format(
            {"text_wrap": True, "num_format": "yyyy-mm-dd"}
        )
        self.datetime_style = self.workbook.add_format(
            {"text_wrap": True, "num_format": "yyyy-mm-dd hh:mm:ss"}
        )
        self.base_style = self.workbook.add_format({"text_wrap": True})
        self.float_style = self.workbook.add_format(
            {"text_wrap": True, "num_format": "#,##0.00"}
        )

        with dbg.timer(self.env, "[xlsx] max currency decimal_places"):
            decimal_places = self.env["res.currency"]._read_group(
                [], aggregates=["decimal_places:max"]
            )[0][0]
        self.monetary_decimal_places = decimal_places or 2
        self.monetary_style = self.workbook.add_format(
            {
                "text_wrap": True,
                "num_format": f"#,##0.{self.monetary_decimal_places * '0'}",
            }
        )

        header_bold_props = {
            "text_wrap": True,
            "bold": True,
            "bg_color": "#e9ecef",
        }
        self.header_bold_style = self.workbook.add_format(header_bold_props)
        self.header_bold_style_float = self.workbook.add_format(
            dict(**header_bold_props, num_format="#,##0.00")
        )
        self.header_bold_style_monetary = self.workbook.add_format(
            dict(
                **header_bold_props,
                num_format=f"#,##0.{self.monetary_decimal_places * '0'}",
            )
        )

        self.value = False
        dbg.lifecycle.debug(
            "[xlsx] writer: %d columns, %d rows, monetary decimals=%d",
            len(columns_headers),
            row_count,
            self.monetary_decimal_places,
        )

    def __enter__(self) -> Self:
        self.write_header()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.close()

    def write_header(self) -> None:
        for i, column_header in enumerate(self.columns_headers):
            self.write(0, i, column_header, self.header_style)
        self.worksheet.freeze_panes(1, 0)

    def close(self) -> None:
        with dbg.timer(None, "[xlsx] autofit"):
            self.worksheet.autofit()
        with dbg.timer(None, "[xlsx] workbook close"):
            self.workbook.close()
        with self.output:
            self.value = self.output.getvalue()
        dbg.performance.debug("[xlsx] closed: %d bytes", len(self.value))

    def write(self, row: int, column: int, cell_value: Any, style: Any = None) -> None:
        error_code = self.worksheet.write(row, column, cell_value, style)
        if error_code:
            dbg.logic.debug(
                "[xlsx] write (%d, %d) %s -> error %s",
                row,
                column,
                type(cell_value).__name__,
                error_code,
            )
        if error_code == -1:
            raise UserError(
                self.env._(
                    "There are too many rows (limit: %(limit)s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.",
                    limit=self.worksheet.xls_rowmax,
                )
            )
        if error_code:
            raise UserError(
                self.env._(
                    "The value of cell (row %(row)s, column %(column)s) could not be written to the XLSX file.",
                    row=row,
                    column=column,
                )
            )

    def write_cell(self, row: int, column: int, cell_value: Any) -> None:
        cell_style = self.base_style

        if isinstance(cell_value, bytes):
            try:
                cell_value = cell_value.decode()
            except UnicodeDecodeError:
                dbg.logic.debug(
                    "[xlsx] (%d, %d) binary not base64 text, refused", row, column
                )
                raise UserError(
                    self.env._(
                        "Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.",
                        self.columns_headers[column],
                    )
                ) from None
        elif isinstance(cell_value, (list, tuple, dict)):
            cell_value = str(cell_value)

        if isinstance(cell_value, str):
            if len(cell_value) > self.worksheet.xls_strmax:
                dbg.logic.debug(
                    "[xlsx] (%d, %d) %d chars > xls_strmax, replaced",
                    row,
                    column,
                    len(cell_value),
                )
                cell_value = self.env._(
                    "The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.",
                    self.worksheet.xls_strmax,
                )
            else:
                cell_value = cell_value.replace("\r", " ")
        elif isinstance(cell_value, datetime.datetime):
            cell_style = self.datetime_style
        elif isinstance(cell_value, datetime.date):
            cell_style = self.date_style
        elif isinstance(cell_value, float):
            field = self.fields[column]
            cell_style = (
                self.monetary_style
                if field.get("type") == "monetary"
                else self.float_style
            )
        self.write(row, column, cell_value, cell_style)


class GroupExportXlsxWriter(ExportXlsxWriter):
    def write_group(
        self,
        row: int,
        column: int,
        group_name: Any,
        group: GroupsTreeNode,
        group_depth: int = 0,
    ) -> tuple[int, int]:
        group_name = (
            group_name[1]
            if isinstance(group_name, tuple) and len(group_name) > 1
            else group_name
        )
        if group._groupby_type[group_depth] != "boolean":
            group_name = group_name or self.env._("Undefined")
        dbg.pipeline.debug(
            "[xlsx] group depth=%d %r: count=%d children=%d rows=%d at row %d",
            group_depth,
            group_name,
            group.count,
            len(group.children),
            len(group.data),
            row,
        )
        row, column = self._write_group_header(
            row, column, group_name, group, group_depth
        )

        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(
                row, column, child_group_name, child_group, group_depth + 1
            )

        for record in group.data:
            row, column = self._write_row(row, column, record)
        return row, column

    def _write_row(self, row: int, column: int, data: list[Any]) -> tuple[int, int]:
        for value in data:
            self.write_cell(row, column, value)
            column += 1
        return row + 1, 0

    def _write_group_header(
        self,
        row: int,
        column: int,
        label: str,
        group: GroupsTreeNode,
        group_depth: int = 0,
    ) -> tuple[int, int]:
        aggregates = group.aggregated_values

        label = f"{'    ' * group_depth}{label} ({group.count})"
        first_field = self.fields[0]
        first_aggregate = aggregates.get(first_field["name"])
        if first_aggregate is not None:
            if first_field.get("type") == "monetary":
                first_aggregate = f"{first_aggregate:,.{self.monetary_decimal_places}f}"
            elif first_field.get("type") == "float":
                first_aggregate = f"{first_aggregate:,.2f}"
            label = f"{label} — {first_aggregate}"
        self.write(row, column, label, self.header_bold_style)
        for field in self.fields[1:]:
            column += 1
            aggregated_value = aggregates.get(field["name"])
            header_style = self.header_bold_style
            if field.get("type") == "monetary":
                header_style = self.header_bold_style_monetary
            elif field.get("type") == "float":
                header_style = self.header_bold_style_float
            else:
                aggregated_value = str(
                    aggregated_value if aggregated_value is not None else ""
                )
            self.write(row, column, aggregated_value, header_style)
        return row + 1, 0


class XlsxRowsWriter(BaseWriter):
    name = "xlsx"
    mimetype = XLSX_MIMETYPE
    consumes = ROWS

    def write(self, value: Any, **options: Any) -> bytes:
        rows = [list(row) for row in value]
        columns_headers = list(options.get("columns_headers") or [])
        width = max((len(row) for row in rows), default=len(columns_headers))
        fields = list(options.get("fields") or [])
        dbg.lifecycle.debug(
            "[xlsx] rows writer: %d rows, width %d, %d fields, %d headers, env=%s",
            len(rows),
            width,
            len(fields),
            len(columns_headers),
            options.get("env") is not None,
        )
        fields += [{"name": "", "type": "char"}] * (width - len(fields))
        with ExportXlsxWriter(
            fields, columns_headers, len(rows), env=options.get("env")
        ) as writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    writer.write_cell(row_index + 1, cell_index, cell_value)
        return writer.value


register_writer(XlsxRowsWriter())
