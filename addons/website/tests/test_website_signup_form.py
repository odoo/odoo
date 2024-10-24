# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteAuthSignupCustomFieldFlow(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['res.config.settings'].create({'auth_signup_uninvited': 'b2c'}).execute()

    def test_website_auth_signup_custom_field(self):
        self.authenticate(None, None)
        country_in = self.env.ref('base.in')
        self.url_open('/web/signup', data={
            'name': 'odoo_bot',
            'login': 'odoo@odoo.com',
            'password': '123456789',
            'confirm_password': '123456789',
            'zip': '380006',
            'city': 'Gandhinagar',
            'country_id': str(country_in.id),
            'field_1': 'this_is_the_text_of_field_1',
            'csrf_token': self.csrf_token(),
        }, files=[
            ('file_1[0][0]', ('image.png', b'fake_file_content', 'image/png')),
        ])

        # Retrieve the partner created from signup
        partner = self.env['res.partner'].search(
            [('name', '=', 'odoo_bot')], limit=1
        )

        # Verify that whitelisted fields are correctly saved on the partner
        self.assertTrue(partner, "Partner 'odoo_bot' should exist")
        self.assertEqual(partner.zip, '380006')
        self.assertEqual(partner.city, 'Gandhinagar')
        self.assertEqual(partner.country_id, country_in)

        # Verify that custom text field is logged in the chatter
        self.assertIn(
            'this_is_the_text_of_field_1',
            ''.join(partner.message_ids.mapped('body')),
        )

        # Verify that the uploaded file is stored as an attachment in chatter
        self.assertIn(
            'image.png',
            partner.message_ids.mapped('attachment_ids.name'),
        )
