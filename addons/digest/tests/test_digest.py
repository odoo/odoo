# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import random

from dateutil.relativedelta import relativedelta
from lxml import html
from werkzeug.urls import url_encode

from odoo import fields, SUPERUSER_ID
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests import common as mail_test
from odoo.tests import tagged
from odoo.tests.common import users


class TestDigest(mail_test.MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestDigest, cls).setUpClass()
        cls._activate_multi_company()

        # clean messages
        cls.env['mail.message'].search([
            ('subtype_id', '=', cls.env.ref('mail.mt_comment').id),
            ('message_type', 'in', ['comment', 'email']),
        ]).unlink()
        cls._setup_messages()

        # clean demo users so that we keep only the test users
        cls.env['res.users'].search([('login', 'in', ['demo', 'portal'])]).action_archive()
        # clean logs so that town down is activated
        cls.env['res.users.log'].search([('create_uid', 'in', (cls.user_admin + cls.user_employee).ids)]).unlink()

        cls.test_digest = cls.env['digest.digest'].create({
            'kpi_mail_message_total': True,
            'kpi_res_users_connected': True,
            'name': "My Digest",
            'periodicity': 'daily',
        })

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
        for count, (low, high) in [(3, (0 * 24,  1 * 24)),
                                   (5, (1 * 24,  7 * 24)),
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
        messages.flush()

    @users('admin')
    def test_digest_numbers(self):
        digest = self.env['digest.digest'].browse(self.test_digest.ids)
        digest._action_subscribe_users(self.user_employee)

        # digest creates its mails in auto_delete mode so we need to capture
        # the formatted body during the sending process
        digest.flush()
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

    @users('admin')
    def test_digest_tone_down(self):
        digest = self.env['digest.digest'].browse(self.test_digest.ids)
        digest._action_subscribe_users(self.user_employee)

        # initial data
        self.assertEqual(digest.periodicity, 'daily')

        # no logs for employee -> should tone down periodicity
        digest.flush()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(digest.periodicity, 'weekly')

        # no logs for employee -> should tone down periodicity
        digest.flush()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(digest.periodicity, 'monthly')

        # no logs for employee -> should tone down periodicity
        digest.flush()
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
    def test_digest_tone_down_wlogs(self):
        digest = self.env['digest.digest'].browse(self.test_digest.ids)
        digest._action_subscribe_users(self.user_employee)

        # initial data
        self.assertEqual(digest.periodicity, 'daily')

        # logs for employee -> should not tone down
        logs = self.env['res.users.log'].with_user(SUPERUSER_ID).create({'create_uid': self.user_employee.id})
        digest.flush()
        with self.mock_mail_gateway():
            digest.action_send()

        logs.unlink()
        logs = self.env['res.users.log'].with_user(SUPERUSER_ID).create({
            'create_uid': self.user_employee.id,
            'create_date': fields.Datetime.now() - relativedelta(days=20),
        })

        # logs for employee are more than 3 days old -> should tone down
        digest.flush()
        with self.mock_mail_gateway():
            digest.action_send()
        self.assertEqual(digest.periodicity, 'weekly')

        # logs for employee are more than 2 weeks old -> should tone down
        digest.flush()
        with self.mock_mail_gateway():
            digest.action_send()
        self.assertEqual(digest.periodicity, 'monthly')

        # logs for employee are less than 1 month old -> should not tone down
        digest.flush()
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
        self.test_digest.invalidate_cache()
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    def test_unsubscribe_public(self):
        """ Check public users are redirected when trying to catch unsubscribe
        route. """
        self.authenticate(None, None)

        response = self._url_unsubscribe()
        self.assertEqual(response.status_code, 404)

    def _url_unsubscribe(self, token=None, user_id=None):
        url_params = {}
        if token is not None:
            url_params['token'] = token
        if user_id is not None:
            url_params['user_id'] = user_id

        url = "%s/digest/%s/unsubscribe?%s" % (
            self.base_url,
            self.test_digest.id,
            url_encode(url_params)
        )
        return self.url_open(url)
