# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_parse, url_decode, url_encode

from odoo.addons.auth_signup.models.res_partner import ResPartner
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase
from odoo.tools import html_escape, mute_logger


@tagged('portal')
class TestPortal(TestMailFullCommon, TestSMSRecipients):

    def setUp(self):
        super().setUp()

        self.record_portal = self.env['mail.test.portal'].create({
            'partner_id': self.partner_1.id,
            'name': 'Test Portal Record',
        })
        self.record_portal._portal_ensure_token()


@tagged('-at_install', 'post_install', 'portal', 'mail_controller')
class TestPortalControllers(TestPortal):

    def test_portal_avatar_with_access_token(self):
        mail_record = self.env['mail.message'].create({
            'author_id': self.record_portal.partner_id.id,
            'model': self.record_portal._name,
            'res_id': self.record_portal.id,
        })
        token = self.record_portal.access_token
        formatted_record = mail_record.portal_message_format(options={"token": token})[0]
        self.assertEqual(
            formatted_record.get("author_avatar_url"),
            f"/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50?access_token={token}",
        )
        response = self.url_open(
            f"/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50?access_token={token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
        self.assertRegex(response.headers.get('Content-Disposition', ''), r'mail_message-\d+-author_avatar\.svg')

        placeholder_response = self.url_open(
            f'/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50?access_token={token + "a"}'
        )  # false token
        self.assertEqual(placeholder_response.status_code, 200)
        self.assertEqual(placeholder_response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(placeholder_response.headers.get('Content-Disposition', ''), r'placeholder\.png')

        no_token_response = self.url_open(f'/mail/avatar/mail.message/{mail_record.id}/author_avatar/50x50')
        self.assertEqual(no_token_response.status_code, 200)
        self.assertEqual(no_token_response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(no_token_response.headers.get('Content-Disposition', ''), r'placeholder\.png')

    def test_portal_avatar_with_hash_pid(self):
        self.authenticate(None, None)
        post_url = f"{self.record_portal.get_base_url()}/mail/message/post"
        pid = self.partner_2.id
        _hash = self.record_portal._sign_token(pid)
        res = self.url_open(
            url=post_url,
            json={
                'params': {
                    'thread_model': self.record_portal._name,
                    'thread_id': self.record_portal.id,
                    'post_data': {'body': "Test"},
                    'hash': _hash,
                    'pid': pid,
                },
            },
        )
        res.raise_for_status()
        self.assertNotIn("error", res.json())
        message = self.record_portal.message_ids[0]
        formatted_message = message.portal_message_format(options={"hash": _hash, "pid": pid})[0]
        self.assertEqual(
            formatted_message.get("author_avatar_url"),
            f"/mail/avatar/mail.message/{message.id}/author_avatar/50x50?_hash={_hash}&pid={pid}",
        )
        response = self.url_open(
            f"/mail/avatar/mail.message/{message.id}/author_avatar/50x50?_hash={_hash}&pid={pid}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
        self.assertRegex(response.headers.get('Content-Disposition', ''), r'mail_message-\d+-author_avatar\.svg')

        placeholder_response = self.url_open(
            f'/mail/avatar/mail.message/{message.id}/author_avatar/50x50?_hash={_hash + "a"}&pid={pid}'
        )  # false hash
        self.assertEqual(placeholder_response.status_code, 200)
        self.assertEqual(placeholder_response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(placeholder_response.headers.get('Content-Disposition', ''), r'placeholder\.png')

    def test_portal_share_comment(self):
        """ Test posting through portal controller allowing to use a hash to
        post wihtout access rights. """
        self.authenticate(None, None)
        post_url = f"{self.record_portal.get_base_url()}/mail/message/post"

        # test as not logged
        self.url_open(
            url=post_url,
            json={
                'params': {
                    'thread_model': self.record_portal._name,
                    'thread_id': self.record_portal.id,
                    'post_data': {'body': "Test"},
                    'token': self.record_portal.access_token,
                    'hash': self.record_portal._sign_token(self.partner_2.id),
                    'pid': self.partner_2.id,
                },
            },
        )
        # Only messages from the current user not OdooBot
        messages = self.record_portal.message_ids.filtered(lambda msg: msg.author_id == self.partner_2)

        self.assertIn('Test', messages[0].body)


@tagged('-at_install', 'post_install', 'portal', 'mail_controller')
class TestPortalFlow(MailCommon, HttpCase):
    """ Test shared links, mail/view links and redirection (backend, customer
    portal or frontend for specific addons). """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.fr').id,
            'email': 'mdelvaux34@example.com',
            'lang': 'en_US',
            'name': 'Mathias Delvaux',
            'phone': '+33353011823',
        })
        # customer portal enabled
        cls.record_portal = cls.env['mail.test.portal'].create({
            'name': 'Test Portal Record',
            'partner_id': cls.customer.id,
            'user_id': cls.user_admin.id,
        })
        # internal only
        cls.record_internal = cls.env['mail.test.track'].create({
            'name': 'Test Internal Record',
        })
        # readable (aka portal can read but no specific action)
        cls.record_read = cls.env['mail.test.simple'].create({
            'name': 'Test Readable Record',
        })
        # 'public' target_type act_url (e.g. blog, forum, ...) -> redirection to a public page
        cls.record_public_act_url = cls.env['mail.test.portal.public.access.action'].create({
            'name': 'Public ActUrl',
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

        # The test relies on `record_access_url` to check the validity of mails being sent,
        # however, when auth_signup is installed, a new token is generated each time the url
        # is being requested.
        # By removing the time-based hashing from this function we can ensure the stability of
        # the url during the tests.
        def patched_generate_signup_token(self, *_, **__):
            self.ensure_one()
            return str([self.id, self._get_login_date(), self.signup_type])
        cls.classPatch(ResPartner, '_generate_signup_token', patched_generate_signup_token)

        # prepare access URLs on self to ease tests
        # ------------------------------------------------------------
        base_url = cls.record_portal.get_base_url()
        cls.test_base_url = base_url

        cls.record_internal_url_base = f'{base_url}/mail/view?model={cls.record_internal._name}&res_id={cls.record_internal.id}'
        cls.record_portal_url_base = f'{base_url}/mail/view?model={cls.record_portal._name}&res_id={cls.record_portal.id}'
        cls.record_read_url_base = f'{base_url}/mail/view?model={cls.record_read._name}&res_id={cls.record_read.id}'
        cls.record_public_act_url_base = f'{base_url}/mail/view?model={cls.record_public_act_url._name}&res_id={cls.record_public_act_url.id}'

        max_internal_id = cls.env['mail.test.track'].search([], order="id desc", limit=1).id
        max_portal_id = cls.env['mail.test.portal'].search([], order="id desc", limit=1).id
        max_read_id = cls.env['mail.test.simple'].search([], order="id desc", limit=1).id
        max_public_act_url_id = cls.env['mail.test.portal.public.access.action'].search([], order="id desc", limit=1).id
        cls.record_internal_url_no_exists = f'{base_url}/mail/view?model={cls.record_internal._name}&res_id={max_internal_id + 1}'
        cls.record_portal_url_no_exists = f'{base_url}/mail/view?model={cls.record_portal._name}&res_id={max_portal_id + 1}'
        cls.record_read_url_no_exists = f'{base_url}/mail/view?model={cls.record_read._name}&res_id={max_read_id + 1}'
        cls.record_public_act_url_url_no_exists = f'{base_url}/mail/view?model={cls.record_public_act_url._name}&res_id={max_public_act_url_id + 1}'

        cls.record_url_no_model = f'{cls.record_portal.get_base_url()}/mail/view?model=this.should.not.exists&res_id=1'

        # find portal + auth data url
        for group_name, group_func, group_data in cls.record_portal.sudo()._notify_get_recipients_groups(
            cls.env['mail.message'], False
        ):
            if group_name == 'portal_customer' and group_func(cls.customer):
                cls.record_portal_url_auth = group_data['button_access']['url']
                break
        else:
            raise AssertionError('Record access URL not found')
        # build altered access_token URL for testing security
        parsed_url = url_parse(cls.record_portal_url_auth)
        query_params = url_decode(parsed_url.query)
        cls.record_portal_hash = query_params['hash']
        cls.record_portal_url_auth_wrong_token = parsed_url.replace(
            query=url_encode({
                **query_params,
                'access_token': query_params['access_token'].translate(
                    str.maketrans('0123456789abcdef', '9876543210fedcba')
                )
            }, sort=True)
        ).to_url()

        # prepare result URLs on self to ease tests
        # ------------------------------------------------------------
        cls.portal_web_url = f'{base_url}/my/test_portal/{cls.record_portal.id}'
        cls.portal_web_url_with_token = f'{base_url}/my/test_portal/{cls.record_portal.id}?{url_encode({"access_token": cls.record_portal.access_token, "pid": cls.customer.id, "hash": cls.record_portal_hash}, sort=True)}'
        cls.public_act_url_share = f'{base_url}/test_portal/public_type/{cls.record_public_act_url.id}'
        cls.internal_backend_local_url = f'/odoo/{cls.record_internal._name}/{cls.record_internal.id}'
        cls.portal_backend_local_url = f'/odoo/{cls.record_portal._name}/{cls.record_portal.id}'
        cls.read_backend_local_url = f'/odoo/{cls.record_read._name}/{cls.record_read.id}'
        cls.public_act_url_backend_local_url = f'/odoo/{cls.record_public_act_url._name}/{cls.record_public_act_url.id}'
        cls.discuss_local_url = '/odoo/action-mail.action_discuss'

    def test_assert_initial_data(self):
        """ Test some initial values. Test that record_portal_url_auth is a valid URL
        to view the record_portal and that record_access_url_wrong_token only differs
        from record_portal_url_auth by a different access_token. """
        self.record_internal.with_user(self.user_employee).check_access('read')
        self.record_portal.with_user(self.user_employee).check_access('read')
        self.record_read.with_user(self.user_employee).check_access('read')

        with self.assertRaises(AccessError):
            self.record_internal.with_user(self.user_portal).check_access('read')
        with self.assertRaises(AccessError):
            self.record_portal.with_user(self.user_portal).check_access('read')
        self.record_read.with_user(self.user_portal).check_access('read')

        self.assertNotEqual(self.record_portal_url_auth, self.record_portal_url_auth_wrong_token)
        url_params = []
        for url in (
            self.record_portal_url_auth, self.record_portal_url_auth_wrong_token,
        ):
            with self.subTest(url=url):
                parsed = url_parse(url)
                self.assertEqual(parsed.path, '/mail/view')
                params = url_decode(parsed.query)
                url_params.append(params)
                # Note that pid, hash and auth_signup_token are not tested by this test but may be present in the URL (config).
                self.assertEqual(params.get('model'), 'mail.test.portal')
                self.assertEqual(int(params.get('res_id')), self.record_portal.id)
                self.assertTrue(params.get('access_token'))
        self.assertNotEqual(url_params[0]['access_token'], url_params[1]['access_token'])
        self.assertEqual(
            {k: v for k, v in url_params[0].items() if k != 'access_token'},
            {k: v for k, v in url_params[1].items() if k != 'access_token'},
            'URLs should be the same, except for access token'
        )

    @users('employee')
    def test_employee_access(self):
        """ Check internal employee behavior when accessing mail/view """
        self.authenticate(self.env.user.login, self.env.user.login)
        for url_name, url, exp_url in [
            # accessible records
            ("Internal record mail/view", self.record_internal_url_base, self.internal_backend_local_url),
            ("Portal record mail/view", self.record_portal_url_base, self.portal_backend_local_url),
            ("Portal readable record mail/view", self.record_read_url_base, self.read_backend_local_url),
            ("Public with act_url", self.record_public_act_url_base, self.public_act_url_backend_local_url),
            # even with token -> backend
            ("Portal record with token", self.record_portal_url_auth, self.portal_backend_local_url),
            # invalid token is not an issue for employee -> backend, has access
            ("Portal record with wrong token", self.record_portal_url_auth_wrong_token, self.portal_backend_local_url),
            # not existing -> redirect to discuss
            ("Not existing record (internal)", self.record_internal_url_no_exists, self.discuss_local_url),
            ("Not existing record (portal enabled)", self.record_portal_url_no_exists, self.discuss_local_url),
            ("Not existign model", self.record_url_no_model, self.discuss_local_url),
        ]:
            with self.subTest(name=url_name, url=url):
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertURLEqual(res.url, exp_url)

    @mute_logger('werkzeug')
    @users('portal_test')
    def test_portal_access_logged(self):
        """ Check portal behavior when accessing mail/view, notably check token
        support and propagation. """
        my_url = f'{self.test_base_url}/my'

        self.authenticate(self.env.user.login, self.env.user.login)
        for url_name, url, exp_url in [
            # valid token -> ok -> redirect to portal URL
            (
                "No access (portal enabled), token", self.record_portal_url_auth,
                self.portal_web_url_with_token,
            ),
            # invalid token -> ko -> redirect to my
            (
                "No access (portal enabled), invalid token", self.record_portal_url_auth_wrong_token,
                my_url,
            ),
            # std url, read record -> redirect to my with parameters being record portal action parameters (???)
            (
                'Access record (no customer portal)', self.record_read_url_base,
                f'{self.test_base_url}/my?{url_encode({"subpath": f"{self.record_read._name}/{self.record_read.id}"})}',
            ),
            # std url, no access to record -> redirect to my
            (
                'No access record (internal)', self.record_internal_url_base,
                my_url,
            ),
            # missing token -> redirect to my
            (
                'No access record (portal enabled)', self.record_portal_url_base,
                my_url,
            ),
            # public_type act_url -> share users are redirected to frontend url
            (
                "Public with act_url -> frontend url", self.record_public_act_url_base,
                self.public_act_url_share
            ),
            # not existing -> redirect to my
            (
                'Not existing record (internal)', self.record_internal_url_no_exists,
                my_url,
            ),
            (
                'Not existing record (portal enabled)', self.record_portal_url_no_exists,
                my_url,
            ),
            (
                'Not existing model', self.record_url_no_model,
                my_url,
            ),
        ]:
            with self.subTest(name=url_name, url=url):
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertURLEqual(res.url, exp_url)

    @mute_logger('werkzeug')
    def test_portal_access_not_logged(self):
        """ Check customer behavior when accessing mail/view, notably check token
        support and propagation. """
        self.authenticate(None, None)
        login_url = f'{self.test_base_url}/web/login'

        for url_name, url, exp_url in [
            # valid token -> ok -> redirect to portal URL
            (
                "No access (portal enabled), token", self.record_portal_url_auth,
                self.portal_web_url_with_token,
            ),
            # invalid token -> ko -> redirect to login with redirect to original link, will be rejected after login
            (
                "No access (portal enabled), invalid token", self.record_portal_url_auth_wrong_token,
                f'{login_url}?{url_encode({"redirect": self.record_portal_url_auth_wrong_token.replace(self.test_base_url, "")})}',
            ),
            # std url, no access to record -> redirect to login with redirect to original link, will be rejected after login
            (
                'No access record (internal)', self.record_internal_url_base,
                f'{login_url}?{url_encode({"redirect": self.record_internal_url_base.replace(self.test_base_url, "")})}',
            ),
            # std url, no access to record but portal -> redirect to login, original (local) URL kept as redirection post login to try again (even if faulty)
            (
                'No access record (portal enabled)', self.record_portal_url_base,
                f'{login_url}?{url_encode({"redirect": self.record_portal_url_base.replace(self.test_base_url, "")})}',
            ),
            (
                'No access record (portal can read, no customer portal)', self.record_read_url_base,
                f'{login_url}?{url_encode({"redirect": self.record_read_url_base.replace(self.test_base_url, "")})}',
            ),
            # public_type act_url -> share users are redirected to frontend url
            (
                "Public with act_url -> frontend url", self.record_public_act_url_base,
                self.public_act_url_share
            ),
            # not existing -> redirect to login, original (internal) URL kept as redirection post login to try again (even if faulty)
            (
                'Not existing record (internal)', self.record_internal_url_no_exists,
                f'{login_url}?{url_encode({"redirect": self.record_internal_url_no_exists.replace(self.test_base_url, "")})}',
            ),
            (
                'Not existing record (portal enabled)', self.record_portal_url_no_exists,
                f'{login_url}?{url_encode({"redirect": self.record_portal_url_no_exists.replace(self.test_base_url, "")})}',
            ),
            (
                'Not existing model', self.record_url_no_model,
                f'{login_url}?{url_encode({"redirect": self.record_url_no_model.replace(self.test_base_url, "")})}',
            ),
        ]:
            with self.subTest(name=url_name, url=url):
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertURLEqual(res.url, exp_url)

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

    @users('employee')
    def test_send_message_to_customer(self):
        """Same as test_send_message_to_customer_using_template but without a template."""
        composer = self.env['mail.compose.message'].with_context(
            self._get_mail_composer_web_context(
                self.record_portal,
                default_email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
            )
        ).create({
            'body': '<p>Hello Mathias Delvaux, your quotation is ready for review.</p>',
            'partner_ids': self.customer.ids,
            'subject': 'Your Quotation "a white table"',
        })

        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer._action_send_mail()

        self.assertEqual(len(self._mails), 1)
        self.assertIn(f'"{html_escape(self.record_portal_url_auth)}"', self._mails[0].get('body'))
        # Check that the template is not used (not the same subject)
        self.assertEqual('Your Quotation "a white table"', self._mails[0].get('subject'))
        self.assertIn('Hello Mathias Delvaux', self._mails[0].get('body'))

    @users('employee')
    def test_send_message_to_customer_using_template(self):
        """Send a mail to a customer without an account and check that it contains a link to view the record.

        Other tests below check that that same link has the correct behavior.
        This test follows the common use case by using a template while the next send the mail without a template."""
        composer = self.env['mail.compose.message'].with_context(
            self._get_mail_composer_web_context(
                self.record_portal,
                default_email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
                default_template_id=self.mail_template.id,
            )
        ).create({})

        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer._action_send_mail()

        self.assertEqual(len(self._mails), 1)
        self.assertIn(f'"{html_escape(self.record_portal_url_auth)}"', self._mails[0].get('body'))
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
