# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from lxml import html
from werkzeug.urls import url_encode, url_join

from odoo import fields, SUPERUSER_ID
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tests import tagged
from odoo.tests.common import users


class TestDigest(TestDigestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestDigest, cls).setUpClass()

        # clean messages
        cls.env['mail.message'].search([
            ('subtype_id', '=', cls.env.ref('mail.mt_comment').id),
            ('message_type', 'in', ('comment', 'email', 'email_outgoing')),
        ]).unlink()
        cls._setup_messages()

        # clean demo users so that we keep only the test users
        cls.env['res.users'].search([('login', 'in', ['demo', 'portal'])]).action_archive()
        # clean logs so that town down is activated
        cls.env['res.users.log'].search([('create_uid', 'in', (cls.user_admin + cls.user_employee).ids)]).unlink()

    @users('admin')
    def test_digest_kpi_res_users_connected_value(self):
        self.env['res.users.log'].search([]).unlink()
        # Sanity check
        initial_values = self.all_digests.mapped('kpi_res_users_connected_value')
        self.assertEqual(initial_values, [0, 0, 0])

        self.env['res.users'].with_user(self.user_employee)._update_last_login()
        self.env['res.users'].with_user(self.user_admin)._update_last_login()

        self.all_digests.invalidate_recordset()

        self.assertEqual(self.digest_1.kpi_res_users_connected_value, 2)
        self.assertEqual(self.digest_2.kpi_res_users_connected_value, 0,
            msg='This KPI is in an other company')
        self.assertEqual(self.digest_3.kpi_res_users_connected_value, 2,
            msg='This KPI has no company, should take the current one')

    @users('admin')
    def test_digest_numbers(self):
        digest = self.env['digest.digest'].browse(self.digest_1.ids)
        digest._action_subscribe_users(self.user_employee)

        # digest creates its mails in auto_delete mode so we need to capture
        # the formatted body during the sending process
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(len(self._new_mails), 1, "A new mail.mail should have been created")
        mail = self._new_mails[0]
        # check mail.mail content
        self.assertEqual(mail.author_id, self.partner_admin)
        self.assertEqual(mail.email_from, self.company_admin.email_formatted)
        self.assertEqual(mail.state, 'outgoing', 'Mail should use the queue')

        kpi_message_values = html.fromstring(mail.body_html).xpath('//table[@data-field="kpi_mail_message_total"]//*[hasclass("kpi_value")]/text()')
        self.assertEqual(
            [t.strip() for t in kpi_message_values],
            ['3', '8', '15']
        )

    @users('admin')
    def test_digest_subscribe(self):
        digest_user = self.digest_1.with_user(self.user_employee)
        self.assertFalse(digest_user.is_subscribed)

        # subscribe a user so at least one mail gets sent
        digest_user.action_subscribe()
        self.assertTrue(
            digest_user.is_subscribed,
            "check the user was subscribed as action_subscribe will silently "
            "ignore subs of non-employees"
        )

    @users('admin')
    def test_digest_tone_down(self):
        digest = self.env['digest.digest'].browse(self.digest_1.ids)
        digest._action_subscribe_users(self.user_employee)

        # initial data
        self.assertEqual(digest.periodicity, 'daily')

        # no logs for employee -> should tone down periodicity
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(digest.periodicity, 'weekly')

        # no logs for employee -> should tone down periodicity
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(digest.periodicity, 'monthly')

        # no logs for employee -> should tone down periodicity
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(digest.periodicity, 'quarterly')

    @users('admin')
    def test_digest_tip_description(self):
        self.env["digest.tip"].create({
            'name': "Test digest tips",
            'tip_description': """
                <t t-set="record_exists" t-value="True" />
                <t t-if="record_exists">
                    <p class="rendered">Record exists.</p>
                </t>
                <t t-else="">
                    <p class="not-rendered">Record doesn't exist.</p>
                </t>
            """,
        })
        with self.mock_mail_gateway():
            self.digest_1._action_send_to_user(self.user_employee)
        self.assertEqual(len(self._new_mails), 1, "A new Email should have been created")
        sent_mail_body = html.fromstring(self._new_mails.body_html)
        values_to_check = [
            sent_mail_body.xpath('//t[@t-set="record_exists"]'),
            sent_mail_body.xpath('//p[@class="rendered"]/text()'),
            sent_mail_body.xpath('//p[@class="not-rendered"]/text()')
        ]
        self.assertEqual(
            values_to_check,
            [[], ['Record exists.'], []],
            "Sent mail should contain properly rendered tip content"
        )

    @users('admin')
    def test_digest_tone_down_wlogs(self):
        digest = self.env['digest.digest'].browse(self.digest_1.ids)
        digest._action_subscribe_users(self.user_employee)

        # initial data
        self.assertEqual(digest.periodicity, 'daily')

        # logs for employee -> should not tone down
        logs = self.env['res.users.log'].with_user(SUPERUSER_ID).create({'create_uid': self.user_employee.id})
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()

        logs.unlink()
        logs = self.env['res.users.log'].with_user(SUPERUSER_ID).create({
            'create_uid': self.user_employee.id,
            'create_date': fields.Datetime.now() - relativedelta(days=20),
        })

        # logs for employee are more than 3 days old -> should tone down
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()
        self.assertEqual(digest.periodicity, 'weekly')

        # logs for employee are more than 2 weeks old -> should tone down
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()
        self.assertEqual(digest.periodicity, 'monthly')

        # logs for employee are less than 1 month old -> should not tone down
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()
        self.assertEqual(digest.periodicity, 'monthly')


@tagged('-at_install', 'post_install')
class TestUnsubscribe(HttpCaseWithUserDemo):

    def setUp(self):
        super(TestUnsubscribe, self).setUp()

        self.test_digest = self.env['digest.digest'].create({
            'kpi_mail_message_total': True,
            'kpi_res_users_connected': True,
            'name': "My Digest",
            'periodicity': 'daily',
            'user_ids': self.user_demo.ids,
        })
        self.test_digest._action_subscribe_users(self.user_demo)
        self.base_url = self.test_digest.get_base_url()
        self.user_demo_unsubscribe_token = self.test_digest._get_unsubscribe_token(self.user_demo.id)

    @users('demo')
    def test_unsubscribe_classic(self):
        self.assertIn(self.user_demo, self.test_digest.user_ids)
        self.authenticate(self.env.user.login, self.env.user.login)

        response = self._url_unsubscribe()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    @users('demo')
    def test_unsubscribe_issues(self):
        """ Test when not being member """
        self.test_digest.write({'user_ids': [(3, self.user_demo.id)]})
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

        # unsubscribe
        self.authenticate(self.env.user.login, self.env.user.login)
        response = self._url_unsubscribe()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    def test_unsubscribe_token(self):
        self.assertIn(self.user_demo, self.test_digest.user_ids)
        self.authenticate(None, None)
        response = self._url_unsubscribe(token=self.user_demo_unsubscribe_token, user_id=self.user_demo.id)
        self.assertEqual(response.status_code, 200)
        self.test_digest.invalidate_recordset()
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    def test_unsubscribe_token_one_click(self):
        self.assertIn(self.user_demo, self.test_digest.user_ids)
        self.authenticate(None, None)

        # Ensure we cannot unregister using GET method (method not allowed)
        response = self._url_unsubscribe(token=self.user_demo_unsubscribe_token, user_id=self.user_demo.id,
                                         one_click='1', method='GET')
        self.assertEqual(response.status_code, 403, 'GET method is forbidden')
        self.test_digest.invalidate_recordset()
        self.assertIn(self.user_demo, self.test_digest.user_ids)

        # Ensure we can unregister with POST method
        response = self._url_unsubscribe(token=self.user_demo_unsubscribe_token, user_id=self.user_demo.id,
                                         one_click='1', method='POST')
        self.assertEqual(response.status_code, 200)
        self.test_digest.invalidate_recordset()
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    def test_unsubscribe_public(self):
        """ Check public users are redirected when trying to catch unsubscribe
        route. """
        self.authenticate(None, None)

        response = self._url_unsubscribe()
        self.assertEqual(response.status_code, 404)

    def _url_unsubscribe(self, token=None, user_id=None, one_click=None, method='GET'):
        url_params = {}
        if token is not None:
            url_params['token'] = token
        if user_id is not None:
            url_params['user_id'] = user_id
        if one_click is not None:
            url_params['one_click'] = one_click

        url = url_join(self.base_url, f'digest/{self.test_digest.id}/unsubscribe?{url_encode(url_params)}')
        if method == 'GET':
            return self.opener.get(url, timeout=10, allow_redirects=True)
        if method == 'POST':
            return self.opener.post(url, timeout=10, allow_redirects=True)
        raise Exception(f'Invalid method {method}')
