import base64
import json
from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import ValidationError

class ValidateSpreadsheetMixinData(TransactionCase):
    def test_onchange_json_data(self):
        spreadsheet_form = Form(self.env["spreadsheet.test"])

        spreadsheet_form.spreadsheet_binary_data = base64.b64encode(json.dumps({'key': 'value'}).encode('utf-8'))
        with self.assertRaises(ValidationError, msg='Invalid JSON Data'):
            spreadsheet_form.spreadsheet_binary_data = base64.b64encode('invalid json'.encode('utf-8'))
