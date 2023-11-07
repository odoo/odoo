# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_parse, url_decode, url_encode, url_unparse

import json

from odoo import http
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase
from odoo.tools import html_escape


@tagged('portal')
class TestPortal(HttpCase, TestMailFullCommon, TestSMSRecipients):

    def setUp(self):
        super(TestPortal, self).setUp()

        self.record_portal = self.env['mail.test.portal'].create({
            'partner_id': self.partner_1.id,
            'name': 'Test Portal Record',
        })

        self.record_portal._portal_ensure_token()


@tagged('-at_install', 'post_install', 'portal')
class TestPortalControllers(TestPortal):

    def test_redirect_to_records(self):
        """ Test redirection of portal-enabled records """
        # Test Case 0: as anonymous, cannot access, redirect to web/login
        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.record_portal._name,
            self.record_portal.id), timeout=15)

        path = url_parse(response.url).path
        self.assertEqual(path, '/web/login')

        # Test Case 1: as admin, can access record
        self.authenticate(self.user_admin.login, self.user_admin.login)
        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.record_portal._name,
            self.record_portal.id), timeout=15)

        self.assertEqual(response.status_code, 200)

        fragment = url_parse(response.url).fragment
        params = url_decode(fragment)
        self.assertEqual(params['cids'], '%s' % self.user_admin.company_id.id)
        self.assertEqual(params['id'], '%s' % self.record_portal.id)
        self.assertEqual(params['model'], self.record_portal._name)

    def test_redirect_to_records_norecord(self):
        """ Check specific use case of missing model, should directly redirect
        to login page. """
        for model, res_id in [
                (False, self.record_portal.id),
                ('', self.record_portal.id),
                (self.record_portal._name, False),
                (self.record_portal._name, ''),
                (False, False),
                ('wrong.model', self.record_portal.id),
                (self.record_portal._name, -4),
            ]:
            response = self.url_open(
                '/mail/view?model=%s&res_id=%s' % (model, res_id),
                timeout=15
            )
            path = url_parse(response.url).path
            self.assertEqual(
                path, '/web/login',
                'Failed with %s - %s' % (model, res_id)
            )

    def test_portal_avatar_image(self):
        mail_record = self.env['mail.message'].create({
            'author_id': self.record_portal.partner_id.id,
            'model': self.record_portal._name,
            'res_id': self.record_portal.id,
        })
        response = self.url_open(f'/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50?access_token={self.record_portal.access_token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(response.headers.get('Content-Disposition', ''), r'mail_message-\d+-author_avatar\.png')

        placeholder_response = self.url_open(f'/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50?access_token={self.record_portal.access_token + "a"}') # false token
        self.assertEqual(placeholder_response.status_code, 200)
        self.assertEqual(placeholder_response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(placeholder_response.headers.get('Content-Disposition', ''), r'placeholder\.png')

        no_token_response = self.url_open(f'/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50')
        self.assertEqual(no_token_response.status_code, 200)
        self.assertEqual(no_token_response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(no_token_response.headers.get('Content-Disposition', ''), r'placeholder\.png')

    def test_portal_message_fetch(self):
        """Test retrieving chatter messages through the portal controller"""
        self.authenticate(None, None)
        message_fetch_url = '/mail/chatter_fetch'

        def get_chatter_message_count():
            return self.make_jsonrpc_request(message_fetch_url, {
                'res_model': 'mail.test.portal',
                'res_id': self.record_portal.id,
                'token': self.record_portal.access_token,
            }).get('message_count', 0)

        self.assertEqual(get_chatter_message_count(), 0)

        for _ in range(8):
            self.record_portal.message_post(
                body='Test',
                author_id=self.partner_1.id,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )

        self.assertEqual(get_chatter_message_count(), 8)

        # Empty the body of a few messages
        for i in (2, 5, 6):
            self.record_portal.message_ids[i].body = ""

        # Empty messages should be ignored
        self.assertEqual(get_chatter_message_count(), 5)

    def test_portal_share_comment(self):
        """ Test posting through portal controller allowing to use a hash to
        post wihtout access rights. """
        self.authenticate(None, None)
        post_url = f"{self.record_portal.get_base_url()}/mail/chatter_post"

        # test as not logged
        self.opener.post(
            url=post_url,
            json={
                'params': {
                    'csrf_token': http.Request.csrf_token(self),
                    'hash': self.record_portal._sign_token(self.partner_2.id),
                    'message': 'Test',
                    'pid': self.partner_2.id,
                    'redirect': '/',
                    'res_model': self.record_portal._name,
                    'res_id': self.record_portal.id,
                    'token': self.record_portal.access_token,
                },
            },
        )
        message = self.record_portal.message_ids[0]

        self.assertIn('Test', message.body)
        self.assertEqual(message.author_id, self.partner_2)


@tagged('portal')
class TestPortalFlow(MailCommon, HttpCase):
    """Share a link by email to a customer without an account for viewing a record through the portal.

    The tests consist in sending a mail related to a record to a customer and checking that the record can be viewed
    through the embedded link:
    - either in the backend if the user is connected and has the right to
    - or in the portal otherwise
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.fr').id,
            'email': 'mdelvaux34@example.com',
            'lang': 'en_US',
            'mobile': '+33639982325',
            'name': 'Mathias Delvaux',
            'phone': '+33353011823',
        })
        cls.record_portal = cls.env['mail.test.portal'].create({
            'name': 'Test Portal Record',
            'partner_id': cls.customer.id,
            'user_id': cls.user_admin.id,
        })
        cls.mail_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>Hello <t t-out="object.partner_id.name"/>, your quotation is ready for review.</p>',
            'email_from': '{{ (object.user_id.email_formatted or user.email_formatted) }}',
            'model_id': cls.env.ref('test_mail_full.model_mail_test_portal').id,
            'name': 'Quotation template',
            'partner_to': '{{ object.partner_id.id }}',
            'subject': 'Your quotation "{{ object.name }}"',
        })
        cls._create_portal_user()
        for group_name, group_func, group_data in cls.record_portal.sudo()._notify_get_recipients_groups(
            cls.env['mail.message'], False
        ):
            if group_name == 'portal_customer' and group_func(cls.customer):
                cls.record_access_url = group_data['button_access']['url']
                break
        else:
            raise AssertionError('Record access URL not found')
        # Build record_access_url_wrong_token with altered access_token for testing security
        parsed_url = url_parse(cls.record_access_url)
        query_params = url_decode(parsed_url.query)
        cls.record_access_url_wrong_token = url_unparse(
            (parsed_url[0], parsed_url[1], parsed_url[2],
             url_encode({**query_params,
                         'access_token': query_params['access_token'].translate(
                             str.maketrans('0123456789abcdef',
                                           '9876543210fedcba'))},
                        sort=True),
             parsed_url[4]))

    def assert_URL(self, url, expected_path, expected_fragment_params=None, expected_query=None):
        """Asserts that the URL has the expected path and if set, the expected fragment parameters and query."""
        parsed_url = url_parse(url)
        fragment_params = url_decode(parsed_url.fragment)
        self.assertEqual(parsed_url.path, expected_path)
        if expected_fragment_params:
            for key, expected_value in expected_fragment_params.items():
                self.assertEqual(fragment_params.get(key), expected_value,
                                 f'Expected: "{key}={expected_value}" (for path: {expected_path})')
        if expected_query:
            self.assertEqual(expected_query, parsed_url.query,
                             f'Expected: query="{expected_query}" (for path: {expected_path})')

    def _get_composer_with_context(self, template_id=False):
        return self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'default_model': self.record_portal._name,
            'default_res_ids': self.record_portal.ids,
            'default_template_id': template_id,
            'force_email': True,
            'lang': '{{ object.partner_id.lang }}',
        })

    def test_initial_data(self):
        """Test some initial values.

        Test that record_access_url is a valid URL to view the record_portal and that record_access_url_wrong_token
        only differs from record_access_url by a different access_token.
        """
        parsed_record_access_url = url_parse(self.record_access_url)
        record_access_query_params = url_decode(parsed_record_access_url.query)
        parsed_record_access_url_wrong_token = url_parse(self.record_access_url_wrong_token)
        record_access_wrong_token_query_params = url_decode(parsed_record_access_url_wrong_token.query)

        self.assertEqual(parsed_record_access_url.path, '/mail/view')
        # Note that pid, hash and auth_signup_token are not tested by this test but may be present in the URL (config).
        self.assertEqual(record_access_query_params.get('model'), 'mail.test.portal')
        self.assertEqual(int(record_access_query_params.get('res_id')), self.record_portal.id)
        self.assertTrue(record_access_query_params.get('access_token'))

        self.assertNotEqual(self.record_access_url, self.record_access_url_wrong_token)
        self.assertEqual(parsed_record_access_url_wrong_token.path, '/mail/view')
        self.assertTrue(record_access_wrong_token_query_params['access_token'])
        self.assertNotEqual(record_access_query_params['access_token'],
                            record_access_wrong_token_query_params['access_token'])
        self.assertEqual({k: v for k, v in record_access_query_params.items() if k != 'access_token'},
                         {k: v for k, v in record_access_wrong_token_query_params.items() if k != 'access_token'})

    @users('portal_test')
    def test_customer_access_logged_without_access(self):
        """Check that the link redirects the customer (without backend access) to the portal for viewing the record."""
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(self.record_access_url)
        self.assertEqual(res.status_code, 200)
        self.assert_URL(res.url, f'/my/test_portal/{self.record_portal.id}')

    @users('portal_test')
    def test_customer_access_logged_without_access_wrong_token(self):
        """Check that it redirects to discuss when logged customer has no access to the record and token is invalid."""
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(self.record_access_url_wrong_token)
        self.assertEqual(res.status_code, 200)
        self.assert_URL(res.url, '/my', {'action': 'mail.action_discuss'})

    def test_customer_access_not_logged(self):
        """Check that the access link redirects the customer (not logged) to the portal for viewing the record."""
        res = self.url_open(self.record_access_url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(f'/my/test_portal/{self.record_portal.id}', res.url)
        self.assert_URL(res.url, f'/my/test_portal/{self.record_portal.id}')

    def test_customer_access_not_logged_wrong_token(self):
        """Check that the access link redirect the customer to login when the token is invalid."""
        res = self.url_open(self.record_access_url_wrong_token)
        self.assertEqual(res.status_code, 200)
        self.assert_URL(res.url, '/web/login', {'model': 'mail.test.portal', 'id': str(self.record_portal.id)},
                        expected_query='redirect=')

    @users('employee')
    def test_employee_access(self):
        """Check that the access link redirects an employee to the backend for viewing the record."""
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(self.record_access_url)
        self.assertEqual(res.status_code, 200)
        self.assert_URL(res.url, '/web', {'model': 'mail.test.portal', 'id': str(self.record_portal.id)})

    @users('employee')
    def test_employee_access_wrong_token(self):
        """Check that the access link redirects an employee to the record even if the token invalid."""
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(self.record_access_url_wrong_token)
        self.assertEqual(res.status_code, 200)
        self.assert_URL(res.url, '/web', {'model': 'mail.test.portal', 'id': str(self.record_portal.id)})

    @users('employee')
    def test_send_message_to_customer(self):
        """Same as test_send_message_to_customer_using_template but without a template."""
        composer = self._get_composer_with_context().create({
            'body': '<p>Hello Mathias Delvaux, your quotation is ready for review.</p>',
            'partner_ids': self.customer.ids,
            'subject': 'Your Quotation "a white table"',
        })

        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer._action_send_mail()

        self.assertEqual(len(self._mails), 1)
        self.assertIn(f'"{html_escape(self.record_access_url)}"', self._mails[0].get('body'))
        # Check that the template is not used (not the same subject)
        self.assertEqual('Your Quotation "a white table"', self._mails[0].get('subject'))
        self.assertIn('Hello Mathias Delvaux', self._mails[0].get('body'))

    @users('employee')
    def test_send_message_to_customer_using_template(self):
        """Send a mail to a customer without an account and check that it contains a link to view the record.

        Other tests below check that that same link has the correct behavior.
        This test follows the common use case by using a template while the next send the mail without a template."""
        composer = self._get_composer_with_context(self.mail_template.id).create({})

        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer._action_send_mail()

        self.assertEqual(len(self._mails), 1)
        self.assertIn(f'"{html_escape(self.record_access_url)}"', self._mails[0].get('body'))
        self.assertEqual(f'Your quotation "{self.record_portal.name}"', self._mails[0].get('subject'))  # Check that the template is used


@tagged('portal')
class TestPortalMixin(TestPortal):

    @users('employee')
    def test_portal_mixin(self):
        """ Test internals of portal mixin """
        customer = self.partner_1.with_env(self.env)
        record_portal = self.env['mail.test.portal'].create({
            'partner_id': customer.id,
            'name': 'Test Portal Record',
        })

        self.assertFalse(record_portal.access_token)
        self.assertEqual(record_portal.access_url, '/my/test_portal/%s' % record_portal.id)

        record_portal._portal_ensure_token()
        self.assertTrue(record_portal.access_token)
