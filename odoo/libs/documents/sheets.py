from __future__ import annotations

import contextlib
import io
from typing import Any

from odoo.libs.numbers import float_repr
from odoo.libs.sheet_names import normalize_excel_sheet_name

from .formats import mimetype_for
from .representations import SHEETS
from .writers import BaseWriter, register_writer

__all__ = ["SheetBuilder"]

EXCEL_DEFAULT_COLUMN_WIDTH = 8.43
SHEET_NAME_MAX_LENGTH = 31
MEASURED_WIDTH_CAP = 75
MEASURED_WIDTH_PADDING = 4


class SheetBuilder:
    # A worksheet recorded as the ordered operations that write it: a column
    # width set after cells were measured replaces what they measured, so the
    # order is part of the sheet.

    def __init__(self, name: str) -> None:
        self.name = name
        self.operations: list[tuple] = []

    def column(self, first: int, last: int, width: float) -> None:
        self.operations.append(("column", first, last, width))

    def row(self, row: int, height: float) -> None:
        self.operations.append(("row", row, height))

    def default_row(self, height: float) -> None:
        self.operations.append(("default_row", height))

    def cell(
        self,
        row: int,
        column: int,
        value: Any,
        style: dict[str, Any] | None = None,
        *,
        rowspan: int = 1,
        colspan: int = 1,
        date: bool = False,
        measure: int | None = None,
    ) -> None:
        self.operations.append(
            (
                "cell",
                row,
                column,
                value,
                dict(style) if style is not None else None,
                rowspan,
                colspan,
                date,
                measure,
            )
        )


class XlsxSheetsWriter(BaseWriter):
    name = "xlsx_sheets"
    mimetype = mimetype_for("xlsx")
    consumes = SHEETS

    def write(self, value: Any, **options: Any) -> bytes:
        import xlsxwriter

        measure_fonts = options.get("measure_fonts") or {}
        decimals = options.get("decimals", 2)
        fonts_by_size: dict[int, dict[str, Any]] = {}
        output = io.BytesIO()
        with xlsxwriter.Workbook(
            output, {"in_memory": True, "strings_to_formulas": False}
        ) as workbook:
            formats: dict[tuple, Any] = {}

            def get_format(props: dict[str, Any] | None) -> Any:
                if props is None:
                    return None
                key = tuple(sorted(props.items()))
                if key not in formats:
                    formats[key] = workbook.add_format(props)
                return formats[key]

            for sheet in value:
                worksheet = workbook.add_worksheet(
                    normalize_excel_sheet_name(sheet.name, workbook.sheetnames) or None
                )
                for operation in sheet.operations:
                    kind = operation[0]
                    if kind == "column":
                        worksheet.set_column(*operation[1:])
                    elif kind == "row":
                        worksheet.set_row(*operation[1:])
                    elif kind == "default_row":
                        worksheet.set_default_row(operation[1])
                    else:
                        (
                            _kind,
                            row,
                            column,
                            cell_value,
                            props,
                            rowspan,
                            colspan,
                            date,
                            measure,
                        ) = operation
                        style = get_format(props)
                        if measure is not None and colspan == 1:
                            fonts = fonts_by_size.get(measure)
                            if fonts is None:
                                fonts = fonts_by_size[measure] = _load_fonts(
                                    measure_fonts, measure
                                )
                            _grow_column(
                                worksheet, fonts, column, cell_value, props, decimals
                            )
                        if colspan == 1 and rowspan == 1:
                            if date:
                                worksheet.write_datetime(row, column, cell_value, style)
                            else:
                                worksheet.write(row, column, cell_value, style)
                        else:
                            worksheet.merge_range(
                                row,
                                column,
                                row + rowspan - 1,
                                column + colspan - 1,
                                cell_value,
                                style,
                            )
        return output.getvalue()


def _load_fonts(paths: dict[str, str], size: int) -> dict[str, Any]:
    from PIL import ImageFont

    fonts = {}
    for font_type in ("Reg", "Bol", "RegIta", "BolIta"):
        try:
            fonts[font_type] = ImageFont.truetype(paths[font_type], size)
        except KeyError, OSError:
            fonts[font_type] = ImageFont.load_default()
    return fonts


def _grow_column(
    worksheet: Any,
    fonts: dict[str, Any],
    column: int,
    value: Any,
    props: dict[str, Any] | None,
    decimals: int,
) -> None:
    props = props or {}
    font = fonts[
        ("Bol" if props.get("bold") else "Reg") + ("Ita" if props.get("italic") else "")
    ]
    try:
        current = worksheet.col_info[column][0]
    except KeyError:
        current = EXCEL_DEFAULT_COLUMN_WIDTH
    if value is None:
        value = ""
    else:
        # a float's repr can run to 17 digits the cell never shows
        with contextlib.suppress(TypeError, ValueError, OverflowError):
            value = float_repr(float(value), decimals)
    text = f"{'  ' * (props.get('indent') or 0)}{value}"
    width = max(font.getlength(line) / 5 for line in text.split("\n"))
    if width > current:
        worksheet.set_column(
            column, column, min(width + MEASURED_WIDTH_PADDING, MEASURED_WIDTH_CAP)
        )


register_writer(XlsxSheetsWriter())
