"""
Patch xlsxwriter to add some sanitization to respect the excel sheet name
restrictions as the sheet name is often translatable, can not control the input

Also write strings as text instead of guessing formulas and urls from them.
"""
import re

import xlsxwriter
from markupsafe import Markup
from xlsxwriter.worksheet import Worksheet


class PatchedXlsxWorksheet(Worksheet):
    def __init__(self):
        super().__init__()
        self.add_write_handler(str, PatchedXlsxWorksheet._write_str)
        self.add_write_handler(Markup, PatchedXlsxWorksheet._write_str)

    def _write_str(self, row, col, *args):
        if args[0]:
            return self.write_string(row, col, *args)
        return None


class PatchedXlsxWorkbook(xlsxwriter.Workbook):
    worksheet_class = PatchedXlsxWorksheet

    def add_worksheet(self, name=None, worksheet_class=None):
        if name:
            # invalid Excel character: []:*?/\
            name = re.sub(r'[\[\]:*?/\\]', '', name)

            # maximum size is 31 characters
            name = name[:31]
        return super().add_worksheet(name, worksheet_class=worksheet_class)


def patch_module():
    xlsxwriter.Workbook = PatchedXlsxWorkbook
