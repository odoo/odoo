# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderSettings(SelfOrderCommonTest):
    def test_self_order_qr_generation(self):

        def validate_url(url, has_table):
            self.assertIn("access_token", url)
            if has_table:
                self.assertIn("table_identifier", url)
            else:
                self.assertNotIn("table_identifier", url)

        def validate_qr_data(qr_data, table_mode):
            self.assertTrue(all(
                k in qr_data
                for k in ("floors", "pos_name", "self_order", "table_example", "table_mode")
            ))
            self.assertEqual(qr_data["table_mode"], table_mode)

        settings = self.env['res.config.settings'].create({
            'pos_config_id': self.pos_config.id,
            'pos_self_ordering_mode': 'mobile',
        })
        for mode, has_table in (('table', True), ('counter', False)):
            settings.pos_self_ordering_service_mode = mode
            qr_data = settings.generate_qr_codes_page()['context']['report_action']['data']
            first_qr_url = qr_data['floors'][0]['table_rows'][0][0]['url']
            example_url = qr_data['table_example']['decoded_url']
            validate_url(first_qr_url, has_table)
            validate_url(example_url, has_table)
            validate_qr_data(qr_data, has_table)
