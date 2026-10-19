# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http.session import session_store
from odoo.tests import common, HttpCase, new_test_user, tagged


@tagged('-at_install', 'post_install')
class TestAuthSignupUninvited(common.TransactionCase):

    def test_01_auth_signup_uninvited(self):
        self.env.ref('base.default_website').auth_signup_uninvited = 'b2c'
        config = self.env['res.config.settings'].create({})
        self.assertEqual(config.auth_signup_uninvited, 'b2c')


@tagged("post_install", "-at_install")
class TestAuthFormsWarning(HttpCase):

    def test_auth_forms_warning(self):
        self.start_tour(self.env["website"].get_client_action_url('/web/login'), 'auth_login_warning', login='admin')
        self.env.ref('base.default_website').auth_signup_uninvited = 'b2c'
        self.start_tour(self.env["website"].get_client_action_url('/web/signup'), 'auth_signup_warning', login='admin')

    def test_signup_specific_user_account(self):
        website = self.env.ref('base.default_website')
        website.write({'auth_signup_uninvited': 'b2c', 'specific_user_account': True})
        self.authenticate(None, None)
        response = self.url_open('/web/signup', data={
            'login': 'signup@example.com',
            'name': 'Signup',
            'password': 'signup@example.com',
            'confirm_password': 'signup@example.com',
            'csrf_token': self.csrf_token(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, '/my')
        user = self.env['res.users'].search([('login', '=', 'signup@example.com')])
        self.assertEqual(user.website_id, website)

    def test_signup_specific_user_account_other_website(self):
        website = self.env['website'].create({
            'name': 'Other Website',
            'auth_signup_uninvited': 'b2c',
            'specific_user_account': True,
        })
        self.authenticate(None, None, session_extra={'force_website_id': website.id})
        self.assertNotEqual(self.session.context['host_id'], website.id)
        response = self.url_open('/web/signup', data={
            'login': 'signup@example.com',
            'name': 'Signup',
            'password': 'signup@example.com',
            'confirm_password': 'signup@example.com',
            'csrf_token': self.csrf_token(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, '/my')
        user = self.env['res.users'].search([('login', '=', 'signup@example.com')])
        self.assertEqual(user.website_id, website)

    def test_signup_specific_user_account_expired_session_with_website(self):
        website = self.env.ref('base.default_website')
        website.write({'auth_signup_uninvited': 'b2c', 'specific_user_account': True})
        new_test_user(self.env, 'expired_portal', groups='base.group_portal', website_id=website.id)
        self.authenticate('expired_portal', 'expired_portal')
        csrf_token = self.csrf_token()
        self.session['session_token'] = 'expired'
        session_store().save(self.session)
        response = self.url_open('/web/signup', data={
            'login': 'signup@example.com',
            'name': 'Signup',
            'password': 'signup@example.com',
            'confirm_password': 'signup@example.com',
            'csrf_token': csrf_token,
        })
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, '/my')
        user = self.env['res.users'].search([('login', '=', 'signup@example.com')])
        self.assertEqual(user.website_id, website)
