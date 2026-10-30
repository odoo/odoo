import base64
import json
from odoo.tests import Form, TransactionCase
from odoo.exceptions import ValidationError
from odoo.addons.spreadsheet.tests.common import SpreadsheetImageTestMixin, SPREADSHEET_DATA_WITH_B64_IMAGE


class ValidateSpreadsheetMixinData(SpreadsheetImageTestMixin, TransactionCase):
    def test_onchange_json_data(self):
        spreadsheet_form = Form(self.env["spreadsheet.test"])

        spreadsheet_form.spreadsheet_binary_data = base64.b64encode(json.dumps({'key': 'value'}).encode('utf-8'))
        with self.assertRaises(ValidationError, msg='Invalid JSON Data'):
            spreadsheet_form.spreadsheet_binary_data = base64.b64encode('invalid json'.encode('utf-8'))

    def test_spreadsheet_pivot(self):
        data = {
            'sheets': [{'id': 'sheet1'}],
            'pivots': {
                '1': {
                    'dataSet': {
                        'zone': {
                            'left': 6,
                            'right': 6,
                            'top': 5,
                            'bottom': 5
                        },
                        'sheetId': 'sheet1'
                    },
                    'columns': [],
                    'rows': [],
                    'measures': [],
                    'name': 'New pivot',
                    'type': 'SPREADSHEET',
                    'formulaId': '1'
                }
            }
        }
        spreadsheet = self.env['spreadsheet.test'].create({
            'spreadsheet_data': json.dumps(data)
        })
        self.assertTrue(spreadsheet.exists())

    def test_spreadsheet_file_name(self):
        spreadsheet = self.env['spreadsheet.test'].create({})
        self.assertEqual(spreadsheet.spreadsheet_file_name, f"{spreadsheet.display_name}.osheet.json")

    def test_create_with_b64_image_on_spreadsheet_data(self):
        spreadsheet = self.env['spreadsheet.test'].create({
            'spreadsheet_data': json.dumps(SPREADSHEET_DATA_WITH_B64_IMAGE)
        })
        self.assert_spreadsheet_image_in_db(spreadsheet)

    def test_create_with_b64_image_on_spreadsheet_binary_data(self):
        spreadsheet = self.env['spreadsheet.test'].create({
            'spreadsheet_binary_data': base64.b64encode(json.dumps(SPREADSHEET_DATA_WITH_B64_IMAGE).encode())
        })
        self.assert_spreadsheet_image_in_db(spreadsheet)

    def test_write_with_b64_image_on_spreadsheet_data(self):
        spreadsheet = self.env['spreadsheet.test'].create({})
        related_attachment_count = self.env['ir.attachment'].search_count([
            ('res_model', '=', spreadsheet._name),
            ('res_id', '=', spreadsheet.id),
            ('mimetype', '=', 'image/gif'),
        ])
        self.assertEqual(related_attachment_count, 0)
        spreadsheet.write({
            'spreadsheet_data': json.dumps(SPREADSHEET_DATA_WITH_B64_IMAGE)
        })
        self.assert_spreadsheet_image_in_db(spreadsheet)

    def test_write_with_b64_image_on_spreadsheet_binary_data(self):
        spreadsheet = self.env['spreadsheet.test'].create({})
        related_attachment_count = self.env['ir.attachment'].search_count([
            ('res_model', '=', spreadsheet._name),
            ('res_id', '=', spreadsheet.id),
            ('mimetype', '=', 'image/gif'),
        ])
        self.assertEqual(related_attachment_count, 0)
        spreadsheet.write({
            'spreadsheet_binary_data': base64.b64encode(json.dumps(SPREADSHEET_DATA_WITH_B64_IMAGE).encode())
        })
        self.assert_spreadsheet_image_in_db(spreadsheet)
