# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import random

from dateutil.relativedelta import relativedelta
from lxml import html

from odoo import fields
from odoo.addons.mail.tests import common as mail_test
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
