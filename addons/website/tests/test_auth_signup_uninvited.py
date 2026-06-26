# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestAuthSignupUninvited(common.TransactionCase):

    def test_01_auth_signup_uninvited(self):
        self.env['website'].browse(1).auth_signup_uninvited = 'b2c'
        config = self.env['res.config.settings'].create({})
        self.assertEqual(config.auth_signup_uninvited, 'b2c')


@tagged("post_install", "-at_install")
class TestAuthFormsWarning(HttpCase):

    def test_auth_forms_warning(self):
        self.env['website'].search([]).auth_signup_uninvited = 'b2c'
        self.start_tour('/web/login', 'auth_login_warning', login='admin')
        self.start_tour('/web/signup', 'auth_signup_warning', login='admin')
