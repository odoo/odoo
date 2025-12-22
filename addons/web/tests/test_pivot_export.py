import io
import json
from lxml import etree
from zipfile import ZipFile

from odoo import http
from odoo.tests.common import HttpCase


class TestPivotExport(HttpCase):

    def test_export_xlsx_with_integer_column(self):
        """ Test the export_xlsx method of the pivot controller with int columns """
        self.authenticate('admin', 'admin')
        jdata = {
            'title': 'Sales Analysis',
            'model': 'sale.report',
            'measure_count': 1,
            'origin_count': 1,
            'col_group_headers': [
                [{'title': 500, 'width': 1, 'height': 1}],
            ],
            'measure_headers': [],
            'origin_headers': [],
            'rows': [
                {'title': 1, 'indent': 0, 'values': [{'value': 42}]},
            ],
        }
        response = self.url_open(
            '/web/pivot/export_xlsx',
            data={
                'data': json.dumps(jdata),
                'csrf_token': http.Request.csrf_token(self),
            },
        )
        response.raise_for_status()
        zip_file = ZipFile(io.BytesIO(response.content))

        with zip_file.open('xl/worksheets/sheet1.xml') as file:
            sheet_tree = etree.parse(file)
        xml_data = {}

        for c in sheet_tree.iterfind('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            cell_ref = c.attrib['r']
            value = c.findtext('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            xml_data[cell_ref] = value

        self.assertEqual(xml_data['B1'], '500')
        self.assertEqual(xml_data['A2'], '0')
        self.assertEqual(xml_data['B2'], '42')
