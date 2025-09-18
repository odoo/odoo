"""XLSX writer classes and grouped-export data structures.

Provides ``ExportXlsxWriter``, ``GroupExportXlsxWriter``, and
``GroupsTreeNode`` — the building blocks used by the CSV / Excel export
controllers in ``export.py``.
"""

import datetime
import functools
import io
import itertools
import logging
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Self

import xlsxwriter

from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


def none_values_filtered[T](
    func: Callable[[Iterable[T]], T | None],
) -> Callable[[Iterable[T | None]], T | None]:
    """Filter out ``None`` values before passing them to *func*."""

    @functools.wraps(func)
    def wrap(iterable: Iterable[T | None]) -> T | None:
        return func(v for v in iterable if v is not None)

    return wrap


def allow_empty_iterable[T](
    func: Callable[[Iterable[T]], T],
) -> Callable[[Iterable[T]], T | None]:
    """Return ``None`` instead of raising when the iterable is empty.

    Some functions do not accept empty iterables (e.g. max, min with no
    default value).  This returns the function *func* such that it returns
    ``None`` if the iterable is empty instead of raising a ``ValueError``.
    """

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
    """An ordered tree of groups built from ``formatted_read_group`` results.

    Each dictionary returned by ``formatted_read_group`` is used to build a
    leaf.  The entire tree is built by inserting all leaves.
    """

    def __init__(
        self,
        model: Any,
        fields: list[str],
        groupby: list[str],
        groupby_type: list[str],
    ) -> None:
        self._model = model
        self._export_field_names = (
            fields  # exported field names (e.g. 'journal_id', 'account_id/name', ...)
        )
        self._groupby = groupby
        self._groupby_type = groupby_type

        self.count: int = 0  # Total number of records in the subtree
        self.children: dict[Any, GroupsTreeNode] = {}
        self.data: list[list[Any]] = []  # Only leaf nodes have data

    def _get_aggregate(
        self, field_name: str, data: Iterator[Any], aggregator: str
    ) -> Any:
        """Compute a single aggregate value for *field_name*."""
        # When exporting one2many fields, multiple data lines might be exported for one record.
        # Blank cells of additionnal lines are filled with an empty string. This could lead to '' being
        # aggregated with an integer or float.
        data = (value for value in data if value != "")

        if aggregator == "avg":
            return self._get_avg_aggregate(field_name, data)

        aggregate_func = OPERATOR_MAPPING.get(aggregator)
        if not aggregate_func:
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
        """Compute a weighted average aggregate for *field_name*."""
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
        """Return field names of exported field having a group operator."""
        aggregated_field_names = []
        for field_name in self._export_field_names:
            if field_name == ".id":
                field_name = "id"
            if "/" in field_name or field_name not in self._model:
                # Currently no support of aggregated value for nested record fields
                # e.g. line_ids/analytic_line_ids/amount
                continue
            field = self._model._fields[field_name]
            if field.aggregator:
                aggregated_field_names.append(field_name)
        return aggregated_field_names

    # Lazy property to memoize aggregated values of children nodes to avoid useless recomputations
    @functools.cached_property
    def aggregated_values(self) -> dict[str, Any]:
        """Return a mapping of field names to their aggregated values."""
        aggregated_values = {}

        # Transpose the data matrix to group all values of each field in one iterable
        field_values = zip(*self.data, strict=True)
        for field_name in self._export_field_names:
            field_data = (self.data and next(field_values)) or []

            if field_name in self._get_aggregated_field_names():
                field = self._model._fields[field_name]
                aggregated_values[field_name] = self._get_aggregate(
                    field_name, field_data, field.aggregator
                )

        return aggregated_values

    def child(self, key: Any) -> GroupsTreeNode:
        """Return the child identified by *key*, creating it if absent.

        :param key: child key identifier (groupby value as returned by
            formatted_read_group, usually ``(id, display_name)``)
        :return: the child node
        """
        if key not in self.children:
            self.children[key] = GroupsTreeNode(
                self._model,
                self._export_field_names,
                self._groupby,
                self._groupby_type,
            )
        return self.children[key]

    def insert_leaf(self, group: dict[str, Any], data: list[list[Any]]) -> None:
        """Build a leaf from *group* and insert it in the tree.

        :param group: dict as returned by ``formatted_read_group``
        """
        leaf_path = [group.get(groupby_field) for groupby_field in self._groupby]
        count = group["__count"]

        # Follow the path from the top level group to the deepest
        # group which actually contains the records' data.
        node = self  # root
        node.count += count
        for node_key in leaf_path:
            # Go down to the next node or create one if it does not exist yet.
            node = node.child(node_key)
            # Update count value and aggregated value.
            node.count += count

        node.data = data


class ExportXlsxWriter:
    """Context-manager that writes rows into a single XLSX worksheet."""

    def __init__(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        row_count: int,
    ) -> None:
        self.fields = fields
        self.columns_headers = columns_headers
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(
            self.output, {"in_memory": True, "constant_memory": True}
        )
        self.header_style = self.workbook.add_format({"bold": True})
        self.date_style = self.workbook.add_format(
            {"text_wrap": True, "num_format": "yyyy-mm-dd"}
        )
        self.datetime_style = self.workbook.add_format(
            {"text_wrap": True, "num_format": "yyyy-mm-dd hh:mm:ss"}
        )
        self.base_style = self.workbook.add_format({"text_wrap": True})
        # FIXME: Should depends of the field digits
        self.float_style = self.workbook.add_format(
            {"text_wrap": True, "num_format": "#,##0.00"}
        )

        # FIXME: Should depends of the currency field for each row (also maybe add the currency symbol)
        decimal_places = request.env["res.currency"]._read_group(
            [], aggregates=["decimal_places:max"]
        )[0][0]
        self.monetary_style = self.workbook.add_format(
            {
                "text_wrap": True,
                "num_format": f"#,##0.{(decimal_places or 2) * '0'}",
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
                num_format=f"#,##0.{(decimal_places or 2) * '0'}",
            )
        )

        self.worksheet = self.workbook.add_worksheet()
        self.value = False

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(
                request.env._(
                    "There are too many rows (%(count)s rows, limit: %(limit)s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.",
                    count=row_count,
                    limit=self.worksheet.xls_rowmax,
                )
            )

    def __enter__(self) -> Self:
        self.write_header()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: Any,
    ) -> None:
        self.close()

    def write_header(self) -> None:
        """Write the column header row and freeze it."""
        for i, column_header in enumerate(self.columns_headers):
            self.write(0, i, column_header, self.header_style)
        self.worksheet.freeze_panes(1, 0)

    def close(self) -> None:
        """Finalize the workbook and capture the output bytes."""
        self.worksheet.autofit()
        self.workbook.close()
        with self.output:
            self.value = self.output.getvalue()

    def write(self, row: int, column: int, cell_value: Any, style: Any = None) -> None:
        """Write a single cell value."""
        self.worksheet.write(row, column, cell_value, style)

    def write_cell(self, row: int, column: int, cell_value: Any) -> None:
        """Write a data cell with automatic style detection."""
        cell_style = self.base_style

        if isinstance(cell_value, bytes):
            try:
                # because xlsx uses raw export, we can get a bytes object
                # here. xlsxwriter does not support bytes values in Python 3 ->
                # assume this is base64 and decode to a string, if this
                # fails note that you can't export
                cell_value = cell_value.decode()
            except UnicodeDecodeError:
                raise UserError(
                    request.env._(
                        "Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.",
                        self.columns_headers[column],
                    )
                ) from None
        elif isinstance(cell_value, (list, tuple, dict)):
            cell_value = str(cell_value)

        if isinstance(cell_value, str):
            if len(cell_value) > self.worksheet.xls_strmax:
                cell_value = request.env._(
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
                self.monetary_style if field["type"] == "monetary" else self.float_style
            )
        self.write(row, column, cell_value, cell_style)


class GroupExportXlsxWriter(ExportXlsxWriter):
    """XLSX writer that renders grouped export data with headers and aggregates."""

    def write_group(
        self,
        row: int,
        column: int,
        group_name: Any,
        group: GroupsTreeNode,
        group_depth: int = 0,
    ) -> tuple[int, int]:
        """Write a group header and its children/data rows."""
        group_name = (
            group_name[1]
            if isinstance(group_name, tuple) and len(group_name) > 1
            else group_name
        )
        if group._groupby_type[group_depth] != "boolean":
            group_name = group_name or request.env._("Undefined")
        row, column = self._write_group_header(
            row, column, group_name, group, group_depth
        )

        # Recursively write sub-groups
        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(
                row, column, child_group_name, child_group, group_depth + 1
            )

        for record in group.data:
            row, column = self._write_row(row, column, record)
        return row, column

    def _write_row(self, row: int, column: int, data: list[Any]) -> tuple[int, int]:
        """Write a single data row."""
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
        """Write a group header row with aggregated values."""
        aggregates = group.aggregated_values

        label = f"{'    ' * group_depth}{label} ({group.count})"
        self.write(row, column, label, self.header_bold_style)
        for field in self.fields[
            1:
        ]:  # No aggregates allowed in the first column because of the group title
            column += 1
            aggregated_value = aggregates.get(field["name"])
            header_style = self.header_bold_style
            if field["type"] == "monetary":
                header_style = self.header_bold_style_monetary
            elif field["type"] == "float":
                header_style = self.header_bold_style_float
            else:
                aggregated_value = str(
                    aggregated_value if aggregated_value is not None else ""
                )
            self.write(row, column, aggregated_value, header_style)
        return row + 1, 0
