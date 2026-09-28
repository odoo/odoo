"""
Patch xlsxwriter to add some sanitization to respect the excel sheet name
restrictions as the sheet name is often translatable, can not control the input

Also write strings as text instead of guessing formulas and urls from them.
"""
import re

import xlsxwriter
from xlsxwriter.worksheet import Worksheet


class PatchedXlsxWorksheet(Worksheet):
    def _write_token_as_string(self, token, row, col, *args):
        # force writing strings
        if not token:
            return self._write_blank(row, col, *args)
        return self._write_string(row, col, *args)


class PatchedXlsxWorkbook(xlsxwriter.Workbook):
    worksheet_class = PatchedXlsxWorksheet

    def __init__(self, filename=None, options=None):
        if issubclass(self.worksheet_class, PatchedXlsxWorksheet):
            options = dict(options or {})
            if any(options.get(opt) for opt in ("strings_to_numbers", "strings_to_formulas", "strings_to_urls")):
                raise ValueError("Strings are always written as text")
            options["strings_to_numbers"] = options["strings_to_formulas"] = options["strings_to_urls"] = False
        super().__init__(filename, options)

    def add_worksheet(self, name=None, worksheet_class=None):
        if name:
            # invalid Excel character: []:*?/\
            name = re.sub(r'[\[\]:*?/\\]', '', name)

            # maximum size is 31 characters
            name = name[:31]
        return super().add_worksheet(name, worksheet_class=worksheet_class)


def patch_module():
    xlsxwriter.Workbook = PatchedXlsxWorkbook
