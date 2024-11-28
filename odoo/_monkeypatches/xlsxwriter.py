import re


try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


def patch_xlsxwriter():
    if xlsxwriter:
        # add some sanitization to respect the excel sheet name restrictions
        # as the sheet name is often translatable, can not control the input
        class PatchedXlsxWorkbook(xlsxwriter.Workbook):
            def add_worksheet(self, name=None, worksheet_class=None):
                if name:
                    # invalid Excel character: []:*?/\
                    name = re.sub(r'[\[\]:*?/\\]', '', name)
                    # maximum size is 31 characters
                    name = name[:31]
                return super(PatchedXlsxWorkbook, self).add_worksheet(name, worksheet_class=None)

        xlsxwriter.Workbook = PatchedXlsxWorkbook
