from base64 import b64encode

from odoo.tools import file_open


def get_file_content(ext):
    with file_open(f'base/tests/files/file.{ext}', 'rb') as file:
        raw = file.read()
        return raw, b64encode(raw)


XLSX_2025_RAW, XLSX_2025_B64 = get_file_content('2025.xlsx')
BMP_RAW, BMP_B64 = get_file_content('bmp')
CSV_RAW, CSV_B64 = get_file_content('csv')
DOC_RAW, DOC_B64 = get_file_content('doc')
DOCX_RAW, DOCX_B64 = get_file_content('docx')
GIF_RAW, GIF_B64 = get_file_content('gif')
ICO_RAW, ICO_B64 = get_file_content('ico')
JPG_RAW, JPG_B64 = get_file_content('jpg')
ODS_RAW, ODS_B64 = get_file_content('ods')
ODT_RAW, ODT_B64 = get_file_content('odt')
PDF_RAW, PDF_B64 = get_file_content('pdf')
PNG_RAW, PNG_B64 = get_file_content('png')
PPT_RAW, PPT_B64 = get_file_content('ppt')
PPTX_RAW, PPTX_B64 = get_file_content('pptx')
SVG_RAW, SVG_B64 = get_file_content('svg')
WEBP_RAW, WEBP_B64 = get_file_content('webp')
XLS_RAW, XLS_B64 = get_file_content('xls')
XLSX_RAW, XLSX_B64 = get_file_content('xlsx')
XML_RAW, XML_B64 = get_file_content('xml')
ZIP_RAW, ZIP_B64 = get_file_content('zip')
