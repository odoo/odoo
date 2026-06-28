# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests.common import TransactionCase
from odoo.tools.binary import BinaryBytes


class TestResConfigSettings(TransactionCase):

    def test_cloud_storage_google_config_encoding(self):
        account_info_dict = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "test-key"
        }
        account_info_str = json.dumps(account_info_dict)

        # Simulates web client uploading a file
        settings = self.env['res.config.settings'].create({
            'cloud_storage_google_service_account_key': BinaryBytes(account_info_str.encode('utf-8')),
        })
        settings._compute_cloud_storage_google_account_info()
        self.assertEqual(settings.cloud_storage_google_account_info, account_info_str, "Human Readable json should be decoded from raw json file bytes")

        # Simulates page refresh;
        self.env['ir.config_parameter'].sudo().set_str('cloud_storage_google_account_info', account_info_str)
        values = settings.get_values()
        key_value = values.get('cloud_storage_google_service_account_key')
        self.assertTrue(key_value, "Key should be present in values")
        self.assertEqual(bytes(key_value), account_info_str.encode('utf-8'), "Key value should be raw bytes of account info")
