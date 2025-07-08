from odoo.tests.common import HttpCase, tagged
import json


@tagged('-at_install', 'post_install')
class TestSaveMulti(HttpCase):

    def test_save_multi_add_operator_and_direct_value(self):
        partner1 = self.env['res.partner'].create({'name': 'Test Partner 1', 'credit_limit': 100.0})
        partner2 = self.env['res.partner'].create({'name': 'Test Partner 2', 'credit_limit': 200.0})

        self.authenticate('admin', 'admin')

        payload = {
            'model': 'res.partner',
            'ids': [partner1.id, partner2.id],
            'changes': {
                'credit_limit': {'operator': '+', 'increment': 50},
                'comment': 'Test update'
            }
        }

        jsonrpc_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": payload
        }

        response = self.url_open('/web/view/save_multi', headers={'Content-Type': 'application/json'}, json=jsonrpc_payload)
        response_content = json.loads(response.content)
        result = response_content.get("result")
        self.assertIsNotNone(result)
        self.assertIn("updated", result)
        self.assertTrue(result["updated"])
        self.assertIn(str(partner1.id), result["updated"])
        self.assertIn(str(partner2.id), result["updated"])
        self.assertIn("credit_limit", result["updated"][str(partner1.id)])
        self.assertIn("comment", result["updated"][str(partner1.id)])

        partner1 = self.env['res.partner'].browse(partner1.id)
        partner2 = self.env['res.partner'].browse(partner2.id)

        self.assertEqual(partner1.credit_limit, 150.0)
        self.assertEqual(partner2.credit_limit, 250.0)
