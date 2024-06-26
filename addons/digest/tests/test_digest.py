# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import random

from ast import literal_eval
from contextlib import contextmanager
from freezegun import freeze_time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import html
from unittest.mock import patch
from werkzeug.urls import url_encode, url_join

from odoo import fields, SUPERUSER_ID
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests import common as mail_test
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestDigest(mail_test.MailCommon):

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
        cls._activate_multi_company()
        cls.reference_datetime = datetime(2024, 2, 13, 13, 30, 0)

        # clean messages
        cls.env['mail.message'].search([
            ('subtype_id', '=', cls.env.ref('mail.mt_comment').id),
            ('message_type', 'in', ['comment', 'email']),
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
    def _setup_messages(cls):
        """ Remove all existing messages, then create a bunch of them on random
        partners with the correct types in correct time-bucket:

        - 3 in the previous 24h
        - 5 more in the 6 days before that for a total of 8 in the previous week
        - 7 more in the 20 days before *that* (because digest doc lies and is
          based around weeks and months not days), for a total of 15 in the
          previous month
        """
        # regular employee can't necessarily access "private" addresses
        partners = cls.env['res.partner'].search([('type', '!=', 'private')])
        messages = cls.env['mail.message']
        counter = itertools.count()

        now = fields.Datetime.now()
        for count, (low, high) in [(3, (0 * 24, 1 * 24)),
                                   (5, (1 * 24, 7 * 24)),
                                   (7, (7 * 24, 27 * 24)),
                                  ]:
            for _ in range(count):
                create_date = now - relativedelta(hours=random.randint(low + 1, high - 1))
                messages += random.choice(partners).message_post(
                    author_id=cls.partner_admin.id,
                    body=f"Awesome Partner! ({next(counter)})",
                    email_from=cls.partner_admin.email_formatted,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    # adjust top and bottom by 1h to avoid overlapping with the
                    # range limit and dropping out of the digest's selection thing
                    create_date=create_date,
                )
        cls.env.flush_all()

    @classmethod
    def _setup_logs_for_users(cls, res_users, log_dt):
        with cls.mock_datetime_and_now(cls, log_dt):
            for user in res_users:
                cls.env['res.users.log'].with_user(user).create({})

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
    def test_digest_numbers(self):
        digest = self.env['digest.digest'].browse(self.test_digest.ids)
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

        kpi_message_values = html.fromstring(mail.body_html).xpath('//div[@data-field="kpi_mail_message_total"]//*[hasclass("kpi_value")]/text()')
        self.assertEqual(
            [t.strip() for t in kpi_message_values],
            ['3', '8', '15']
        )

    @users('admin')
    def test_digest_subscribe(self):
        digest_user = self.test_digest.with_user(self.user_employee)
        self.assertFalse(digest_user.is_subscribed)

        # subscribe a user so at least one mail gets sent
        digest_user.action_subscribe()
        self.assertTrue(
            digest_user.is_subscribed,
            "check the user was subscribed as action_subscribe will silently "
            "ignore subs of non-employees"
        )

        # unsubscribe
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
            self.test_digest._action_send_to_user(self.user_employee)
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
        digest = self.env['digest.digest'].browse(self.test_digest.ids)
        digest._action_subscribe_users(self.user_employee)

        for logs, (periodicity, run_date), (exp_periodicity, exp_run_date, msg) in zip(
            [
                # daily
                [(self.user_employee, self.reference_datetime)],
                [(self.user_employee, self.reference_datetime - relativedelta(days=1, hours=23))],  # two days logs -> do not tone down
                [(self.user_employee, self.reference_datetime - relativedelta(days=2, hours=1))],  # > two days logs -> tone down
                [],  # no logs -> tone down
                # weekly
                [(self.user_employee, self.reference_datetime - relativedelta(days=6))],
                [(self.user_employee, self.reference_datetime - relativedelta(days=8))],  # old logs -> tone down
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
                ('quarterly', self.reference_datetime.date()),
            ],
            [
                ('daily', self.reference_datetime.date() + relativedelta(days=1), 'Daily ok'),  # just push date
                ('daily', self.reference_datetime.date() + relativedelta(days=1), 'Daily ok, 2 days - 1 hour'),  # just push date
                ('weekly', self.reference_datetime.date() + relativedelta(weeks=1), 'Daily old logs (2 days + 1 hour)'),  # tone down on daily
                ('weekly', self.reference_datetime.date() + relativedelta(weeks=1), 'Daily no logs'),  # tone down on daily
                # weekly
                ('weekly', self.reference_datetime.date() + relativedelta(weeks=1), 'Weekly ok'),  # just push date
                ('monthly', self.reference_datetime.date() + relativedelta(months=1), 'Weekly old logs'),  # tone down on weekly
                ('monthly', self.reference_datetime.date() + relativedelta(months=1), 'Weekly no logs'),  # tone down on weekly
                # monthly
                ('monthly', self.reference_datetime.date() + relativedelta(months=1), 'Monthly ok'),  # just push date
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3), 'Monthly old logs'),  # tone down on monthly
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3), 'Monthly no logs'),  # tone down on monthly
                # quarterly
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3), 'Quaterly ok'),  # just push date
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3), 'Quaterly ok'),  # just push date
                ('quarterly', self.reference_datetime.date() + relativedelta(months=3), 'Quaterly ok'),  # just push date
            ],
        ):
            with self.subTest(logs=logs, msg=msg, periodicity=periodicity, run_date=run_date):
                digest.write({
                    'next_run_date': run_date,
                    'periodicity': periodicity,
                })
                for log_user, log_dt in logs:
                    with self.mock_datetime_and_now(log_dt):
                        self.env['res.users.log'].with_user(log_user).create({})

                with self.mock_datetime_and_now(self.reference_datetime), \
                     self.mock_mail_gateway():
                    digest.action_send()

                self.assertEqual(digest.next_run_date, exp_run_date)
                self.assertEqual(digest.periodicity, exp_periodicity)
                self.env['res.users.log'].sudo().search([]).unlink()


@tagged("digest", "mail_mail", "-at_install", "post_install")
class TestUnsubscribe(mail_test.MailCommon, HttpCaseWithUserDemo):

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

    def test_mail_mail_headers(self):
        """ Test mail generated for digest contains unsubscribe headers """
        digest = self.env['digest.digest'].browse(self.test_digest.ids)
        digest._action_subscribe_users(self.user_employee)

        with self.mock_mail_gateway():
            digest.action_send()

        # find outgoing mail, click on unsubscribe link
        for user in self.user_employee + self.user_demo:
            mail = self._find_mail_mail_wemail(user.email_formatted, "outgoing")
            headers = literal_eval(mail.headers)
            unsubscribe_url = headers.get("List-Unsubscribe", "").strip("<>")
            self.assertTrue(unsubscribe_url)
            self.opener.post(unsubscribe_url)

        self.assertFalse(digest.user_ids, "Users should have been unsubscribed from digest")

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

    def test_unsubscribe_token_one_click(self):
        """ Test one-click: should be ok with POST, not GET to avoid link crawling """
        self.assertIn(self.user_demo, self.test_digest.user_ids)
        self.authenticate(None, None)

        with mute_logger('odoo.addons.http_routing.models.ir_http'):
            # Ensure we cannot unregister using GET method (method not allowed)
            response = self._url_unsubscribe(token=self.user_demo_unsubscribe_token, user_id=self.user_demo.id,
                                             one_click='1', method='GET')
        self.assertEqual(response.status_code, 405, 'GET method is not allowed')
        self.assertIn(self.user_demo, self.test_digest.user_ids)

        # Ensure we can unregister with POST method
        response = self._url_unsubscribe(token=self.user_demo_unsubscribe_token, user_id=self.user_demo.id,
                                         one_click='1', method='POST')
        self.assertEqual(response.status_code, 200, 'Valid one-click unsubscribe just returns an OK 200')
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    def _url_unsubscribe(self, token=None, user_id=None, one_click=None, method='GET'):
        url_params = {}
        if token is not None:
            url_params['token'] = token
        if user_id is not None:
            url_params['user_id'] = user_id
        if one_click is not None:
            unsubscribe_route = "unsubscribe_oneclik"
        else:
            unsubscribe_route = "unsubscribe"

        url = url_join(self.base_url, f'digest/{self.test_digest.id}/{unsubscribe_route}?{url_encode(url_params)}')
        if method == 'GET':
            return self.opener.get(url, timeout=10, allow_redirects=True)
        if method == 'POST':
            return self.opener.post(url, timeout=10, allow_redirects=True)
        raise Exception(f'Invalid method {method}')
