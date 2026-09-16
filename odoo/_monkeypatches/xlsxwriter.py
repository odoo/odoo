from typing import Any

import xlsxwriter

from ._excel_utils import normalize_excel_sheet_name


class PatchedXlsxWorkbook(xlsxwriter.Workbook):
    def __init__(
        self, filename: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        options = dict(options or {})
        options.setdefault("strings_to_formulas", False)
        super().__init__(filename, options)

    def _sanitized(self, name: str | None) -> str | None:
        if not name:
            return name
        return normalize_excel_sheet_name(
            name, [sheet.name for sheet in self.worksheets()]
        )

    def add_worksheet(
        self, name: str | None = None, worksheet_class: type | None = None
    ) -> Any:
        return super().add_worksheet(
            self._sanitized(name), worksheet_class=worksheet_class
        )

    def add_chartsheet(
        self, name: str | None = None, chartsheet_class: type | None = None
    ) -> Any:
        return super().add_chartsheet(
            self._sanitized(name), chartsheet_class=chartsheet_class
        )


def patch_module() -> None:
    xlsxwriter.Workbook = PatchedXlsxWorkbook
