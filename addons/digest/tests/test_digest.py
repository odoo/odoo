# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from freezegun import freeze_time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import html
from unittest.mock import patch
from werkzeug.urls import url_encode, url_join

from odoo import SUPERUSER_ID
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tests import tagged
from odoo.tests.common import users


class TestDigest(TestDigestCommon):

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        """ Used when synchronization date (using env.cr.now()) is important
        in addition to standard datetime mocks. Used mainly to detect sync
        issues. """
        with freeze_time(mock_dt), \
             patch.object(self.env.cr, 'now', lambda: mock_dt):
            yield

    @classmethod
    def setUpClass(cls):
        super(TestDigest, cls).setUpClass()
        cls.reference_datetime = datetime(2024, 2, 13, 13, 30, 0)

        # clean messages
        cls.env['mail.message'].search([
            ('subtype_id', '=', cls.env.ref('mail.mt_comment').id),
            ('message_type', 'in', ('comment', 'email', 'email_outgoing')),
        ]).unlink()
        cls._setup_messages()

        # clean demo users so that we keep only the test users
        cls.env['res.users'].search([('login', 'in', ['demo', 'portal'])]).action_archive()
        # clean logs so that town down can be tested
        cls.env['res.users.log'].search([('create_uid', 'in', (cls.user_admin + cls.user_employee).ids)]).unlink()
        # create logs for user_admin
        cls._setup_logs_for_users(cls.user_admin, cls.reference_datetime - relativedelta(days=5))

        with cls.mock_datetime_and_now(cls, cls.reference_datetime):
            cls.test_digest, cls.test_digest_2 = cls.env['digest.digest'].create([
                {
                    "kpi_mail_message_total": True,
                    "kpi_res_users_connected": True,
                    "name": "My Digest",
                    "periodicity": "daily",
                }, {
                    "kpi_mail_message_total": True,
                    "kpi_res_users_connected": True,
                    "name": "My Digest",
                    "periodicity": "weekly",
                    "user_ids": [(4, cls.user_admin.id), (4, cls.user_employee.id)],
                }
            ])

    @classmethod
    def _setup_logs_for_users(cls, res_users, log_dt):
        with cls.mock_datetime_and_now(cls, log_dt):
            for user in res_users:
                cls.env['res.users.log'].with_user(SUPERUSER_ID).create({
                    'create_uid': user.id,
                })

    @users('admin')
    def test_assert_initial_values(self):
        """ Ensure base values for tests """
        test_digest = self.test_digest.with_user(self.env.user)
        test_digest_2 = self.test_digest_2.with_user(self.env.user)
        self.assertEqual(test_digest.create_date, self.reference_datetime)
        self.assertEqual(test_digest.next_run_date, self.reference_datetime.date() + relativedelta(days=1))
        self.assertEqual(test_digest.periodicity, 'daily')
        self.assertFalse(test_digest.user_ids)

        self.assertEqual(test_digest_2.create_date, self.reference_datetime)
        self.assertEqual(test_digest_2.next_run_date, self.reference_datetime.date() + relativedelta(weeks=1))
        self.assertEqual(test_digest_2.periodicity, 'weekly')
        self.assertEqual(test_digest_2.user_ids, self.user_admin + self.user_employee)

    @users('admin')
    def test_digest_kpi_res_users_connected_value(self):
        self.env['res.users.log'].with_user(SUPERUSER_ID).search([]).unlink()
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
        digest_user.action_unsubscribe()
        self.assertFalse(digest_user.is_subscribed)

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
    def test_digest_tone_down(self):
        test_digest = self.env['digest.digest'].browse(self.test_digest.ids)
        test_digest_2 = self.env['digest.digest'].browse(self.test_digest_2.ids)
        test_digest._action_subscribe_users(self.user_employee)
        digests = test_digest + test_digest_2  # batch recordset

        # no logs for employee but for admin -> should tone down periodicity of
        # first digest, not the second one (admin being subscribed)
        digests.flush_recordset()
        current_dt = self.reference_datetime + relativedelta(days=1)
        with self.mock_datetime_and_now(current_dt), \
             self.mock_mail_gateway():
            digests.action_send()

        self.assertEqual(test_digest.next_run_date, current_dt.date() + relativedelta(weeks=1))
        self.assertEqual(test_digest.periodicity, 'weekly')
        self.assertEqual(test_digest_2.next_run_date, current_dt.date() + relativedelta(weeks=1))
        self.assertEqual(test_digest_2.periodicity, 'weekly',
                         'Should not have tone down because admin has logs')

        # no logs for employee -> should tone down periodicity
        with self.mock_datetime_and_now(current_dt), \
             self.mock_mail_gateway():
            digests.action_send()

        self.assertEqual(test_digest.next_run_date, current_dt.date() + relativedelta(months=1))
        self.assertEqual(test_digest.periodicity, 'monthly')
        self.assertEqual(test_digest_2.next_run_date, current_dt.date() + relativedelta(weeks=1))
        self.assertEqual(test_digest_2.periodicity, 'weekly')

        # no logs for employee -> should tone down periodicity
        with self.mock_datetime_and_now(current_dt), \
             self.mock_mail_gateway():
            digests.action_send()

        self.assertEqual(test_digest.next_run_date, current_dt.date() + relativedelta(months=3))
        self.assertEqual(test_digest.periodicity, 'quarterly')
        self.assertEqual(test_digest_2.next_run_date, current_dt.date() + relativedelta(weeks=1))
        self.assertEqual(test_digest_2.periodicity, 'weekly')

    @users('admin')
    def test_digest_tone_down_wlogs(self):
        digest = self.env['digest.digest'].browse(self.digest_1.ids)
        digest._action_subscribe_users(self.user_employee)

        for logs, (periodicity, run_date), (exp_periodicity, exp_run_date) in zip(
            [
                # daily
                [(self.user_employee, self.reference_datetime)],
                [(self.user_employee, self.reference_datetime - relativedelta(days=4))],  # old logs -> tone down
                [],  # no logs -> tone down
                # weekly
                [(self.user_employee, self.reference_datetime - relativedelta(days=8))],
                [(self.user_employee, self.reference_datetime - relativedelta(days=15))],  # old logs -> tone down
                [],  # no logs -> tone down
                # monthly
                [(self.user_employee, self.reference_datetime - relativedelta(days=25))],
                [(self.user_employee, self.reference_datetime - relativedelta(days=32))],  # old logs -> tone down
                [],  # no logs -> tone down
                # quarterly
                [(self.user_employee, self.reference_datetime - relativedelta(months=2))],
                [(self.user_employee, self.reference_datetime - relativedelta(months=4))],  # old logs but end of tone down
                [],  # no logs but end of town down
            ],
            [
                # daily
                ('daily', self.reference_datetime.date()),
                ('daily', self.reference_datetime.date()),
                ('daily', self.reference_datetime.date()),
                # weekly
                ('weekly', self.reference_datetime.date()),
                ('weekly', self.reference_datetime.date()),
                ('weekly', self.reference_datetime.date()),
                # monthly
                ('monthly', self.reference_datetime.date()),
                ('monthly', self.reference_datetime.date()),
                ('monthly', self.reference_datetime.date()),
                # quarterly
                ('quarterly', self.reference_datetime.date()),
                ('quarterly', self.reference_datetime.date()),
                # ('quarterly', self.reference_datetime.date()),
            ],
            [
                ('daily', self.reference_datetime.date() + relativedelta(days=1)),  # just push date
                ('weekly', self.reference_datetime.date() + relativedelta(weeks=1)),  # tone down on daily
                ('weekly', self.reference_datetime.date() + relativedelta(weeks=1)),  # tone down on daily
                # weekly
                ('weekly', self.reference_datetime.date() + relativedelta(weeks=1)),  # just push date
                ('monthly', self.reference_datetime.date() + relativedelta(months=1)),  # tone down on weekly
                ('monthly', self.reference_datetime.date() + relativedelta(months=1)),  # tone down on weekly
                # monthly
                ('monthly', self.reference_datetime.date() + relativedelta(months=1)),  # just push date
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3)),  # tone down on monthly
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3)),  # tone down on monthly
                # quarterly
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3)),  # just push date
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3)),  # just push date
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3)),  # just push date
            ],
        ):
            with self.subTest(logs=logs, periodicity=periodicity, run_date=run_date):
                digest.write({
                    'next_run_date': run_date,
                    'periodicity': periodicity,
                })
                for log_user, log_dt in logs:
                    self._setup_logs_for_users(log_user, log_dt)

                with self.mock_datetime_and_now(run_date), \
                     self.mock_mail_gateway():
                    digest.action_send()

                self.assertEqual(digest.next_run_date, exp_run_date)
                self.assertEqual(digest.periodicity, exp_periodicity)
                self.env['res.users.log'].with_user(SUPERUSER_ID).search([]).unlink()


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

    def test_unsubscribe(self):
        """ Test various combination of unsubscribe: logged, using token, ... """
        digest = self.test_digest
        demo_token = digest._get_unsubscribe_token(self.user_demo.id)
        for test_user, is_member, is_logged, token, exp_code in [
            (self.user_demo, True, True, False, 200),  # unsubscribe logged, easy
            (self.user_demo, False, True, False, 200),  # unsubscribe not a member should not crash
            (self.user_demo, False, False, demo_token, 200),  # unsubscribe using a token
            (self.user_demo, False, False, 'probably-not-a-token', 404),  # wrong token -> crash
            (self.user_demo, False, False, False, 404),  # cannot be done unlogged / no token
        ]:
            with self.subTest(user_name=test_user.name, is_member=is_member, is_logged=is_logged, token=token):
                if is_member:
                    digest._action_subscribe_users(test_user)
                    self.assertIn(test_user, digest.user_ids)
                else:
                    digest._action_unsubscribe_users(test_user)
                    self.assertNotIn(test_user, digest.user_ids)

                self.authenticate(test_user.login if is_logged else None, test_user.login if is_logged else None)
                if token:
                    response = self._url_unsubscribe(token=token, user_id=test_user.id)
                else:
                    response = self._url_unsubscribe()
                self.assertEqual(response.status_code, exp_code)
                self.assertNotIn(test_user, digest.user_ids)

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
