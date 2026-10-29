# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSignupForm(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['res.config.settings'].create({'auth_signup_uninvited': 'b2c'}).execute()

    def test_website_signup_form(self):
        """ The fields added on the signup form from the editor are saved on the
        page: on signup, the values of the existing ones are written on the
        partner, the ones of the custom fields are logged in its chatter. """
        self.start_tour(
            self.env['website'].get_client_action_url('/web/signup', True),
            'website_signup_form',
            login='admin',
        )

        partner = self.env['res.users'].search([('login', '=', 'test.submit@example.com')]).partner_id
        self.assertTrue(partner, "The browser should have submitted the signup form")
        self.assertEqual(partner.city, "Grand-Rosière", "An existing field is written on the partner")
        self.assertEqual(partner.phone, "+32 495 00 00 00", "An existing field is written on the partner")
        log_note = next(
            message for message in partner.message_ids if "Other Information" in message.body
        )
        self.assertIn("Notes : yes please", log_note.body, "A custom field is logged in the chatter")
        self.assertIn("Comments : From the editor", log_note.body)
