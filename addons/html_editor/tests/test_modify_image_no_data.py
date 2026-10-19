
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import odoo.tests
from odoo.tests.common import HttpCase
from odoo.tools.json import scriptsafe as json_safe


@odoo.tests.tagged('-at_install', 'post_install')
class TestModifyImageNoData(HttpCase):

    def setUp(self):
        super().setUp()
        self.authenticate('admin', 'admin')

    def test_modify_image_no_data(self):
        # Create an attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'test_image.gif',
            'raw': base64.b64decode(b'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='),
            'res_model': 'ir.ui.view',
            'res_id': 0,
        })

        # Call the modify_image controller without the 'data' parameter
        response = self.url_open(
            f'/html_editor/modify_image/{attachment.id}',
            headers={'Content-Type': 'application/json'},
            data=json_safe.dumps({'params': {
                'res_model': 'ir.ui.view',
                'res_id': 0,
                'name': 'modified_image.gif',
            }})
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertNotIn('error', response_data)
        self.assertIn('result', response_data)

        modified_attachment = self.env['ir.attachment'].search([
            ('name', '=', 'modified_image.gif'),
            ('original_id', '=', attachment.id),
        ])
        self.assertEqual(len(modified_attachment), 1)
