"""
Patch xlwt to add some sanitization to respect the excel sheet name
restrictions as the sheet name is often translatable, can not control the input
"""
import re

import xlwt


class PatchedWorkbook(xlwt.Workbook):
    def add_sheet(self, name, cell_overwrite_ok=False):
        # invalid Excel character: []:*?/\
        name = re.sub(r'[\[\]:*?/\\]', '', name)

        # maximum size is 31 characters
        name = name[:31]
        return super().add_sheet(name, cell_overwrite_ok=cell_overwrite_ok)


def patch_module():
    xlwt.Workbook = PatchedWorkbook
