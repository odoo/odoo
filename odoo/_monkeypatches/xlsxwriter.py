"""
Patch xlsxwriter to add some sanitization to respect the excel sheet name
restrictions as the sheet name is often translatable, can not control the input
"""
import re

import xlsxwriter


class PatchedXlsxWorkbook(xlsxwriter.Workbook):
    def add_worksheet(self, name=None, worksheet_class=None):
        if name:
            # invalid Excel character: []:*?/\
            name = re.sub(r'[\[\]:*?/\\]', '', name)

            # maximum size is 31 characters
            name = name[:31]
        return super().add_worksheet(name, worksheet_class=worksheet_class)


def patch_module():
    xlsxwriter.Workbook = PatchedXlsxWorkbook
