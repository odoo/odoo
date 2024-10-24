# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteAuthSignupCustomFieldFlow(HttpCase):

    def setUp(self):
        super().setUp()
        self.env["res.config.settings"].create({"auth_signup_uninvited": "b2c"}).execute()

    def test_website_auth_signup_custom_field(self):
        self.start_tour("/web/signup", "website_signup_form_add_custom_field", login="admin")
        self.start_tour("/web/login", "website_signup_custom_form_submit", login=None)
