# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from lxml import html

from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSignupForm(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['res.config.settings'].create({'auth_signup_uninvited': 'b2c'}).execute()

    def test_website_signup_form(self):
        """ The signup form is edited with the form builder: the fields added
        from the editor are saved on the page and, on signup, the values of the
        existing ones are written on the partner, the ones of the custom fields
        are logged in its chatter. """
        self.start_tour(
            self.env['website'].get_client_action_url('/web/signup', True),
            'website_signup_form',
            login='admin',
        )

        view = self.env['ir.ui.view'].search([
            ('key', '=', 'website.signup_form'), ('website_id', '!=', False),
        ])
        [form] = html.fromstring(view.arch).xpath("//form[@id='o_signup_form']")
        self.assertFalse(
            form.xpath(".//owl-component | .//input[@type='hidden'] | .//*[@autocomplete='username']"),
            "What depends on the request is not saved with the form",
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

    def test_website_signup_form_error(self):
        """ The signup form is displayed again with the error of a failed
        signup, and the values of its standard fields are given back to it. """
        self.authenticate(None, None)
        response = self.url_open('/web/signup', data={
            'name': "Error Signup",
            'login': 'error.signup@example.com',
            'password': 'Error.Signup1',
            'confirm_password': 'Error.Signup2',
            'csrf_token': self.csrf_token(),
        })

        self.assertFalse(self.env['res.users'].search([('login', '=', 'error.signup@example.com')]))
        self.assertIn("Passwords do not match; please retype them.", response.text)
        data_for = html.fromstring(response.text).xpath("//*[@data-for='o_signup_form']")
        self.assertEqual(
            json.loads(data_for[0].get('data-values')),
            {'name': "Error Signup", 'login': 'error.signup@example.com'},
        )

    def test_website_signup_form_captcha(self):
        """ The captcha token posted along with the signup form is not taken for
        the value of a custom field. """
        self.authenticate(None, None)
        self.url_open('/web/signup', data={
            'name': "Captcha Signup",
            'login': 'captcha.signup@example.com',
            'password': 'Captcha.Signup1',
            'confirm_password': 'Captcha.Signup1',
            'csrf_token': self.csrf_token(),
            'Notes': "yes please",
            'recaptcha_token_response': 'captcha-token',
        })

        partner = self.env['res.users'].search([('login', '=', 'captcha.signup@example.com')]).partner_id
        self.assertTrue(partner, "The signup form should have been submitted")
        log_note = next(
            message for message in partner.message_ids if "Other Information" in message.body
        )
        self.assertIn("Notes : yes please", log_note.body)
        self.assertNotIn("captcha-token", log_note.body, "The captcha token is not a custom field")
