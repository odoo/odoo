# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase


@tagged('portal')
class TestPortal(HttpCase):

    def setUp(self):
        super(TestPortal, self).setUp()

        self.user_employee = mail_new_test_user(
            self.env,
            groups='base.group_user',
            login='employee',
            name='Ernest Employee',
            signature='--\nErnest',
        )
        self.partner_1, self.partner_2 = self.env['res.partner'].create([
            {'name': 'Valid Lelitre',
             'email': 'valid.lelitre@agrolait.com',
             'country_id': self.env.ref('base.be').id,
             'mobile': '0456001122'},
            {'name': 'Valid Poilvache',
             'email': 'valid.other@gmail.com',
             'country_id': self.env.ref('base.be').id,
             'mobile': '+32 456 22 11 00'}
        ])

        self.record_portal = self.env['mail.test.portal'].create({
            'partner_id': self.partner_1.id,
            'name': 'Test Portal Record',
        })

        self.record_portal._portal_ensure_token()

    def test_portal_message_fetch(self):
        """Test retrieving chatter messages through the portal controller"""
        self.authenticate(None, None)
        message_fetch_url = '/mail/chatter_fetch'
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                'res_model': 'mail.test.portal',
                'res_id': self.record_portal.id,
                'token': self.record_portal.access_token,
            },
        })

        def get_chatter_message_count():
            res = self.url_open(
                url=message_fetch_url,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            return res.json().get('result', {}).get('message_count', 0)

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

    def test_portal_share_comment(self):
        """ Test posting through portal controller allowing to use a hash to
        post wihtout access rights. """
        self.authenticate(None, None)
        post_url = "/mail/chatter_post"
        post_data = {
            'csrf_token': http.WebRequest.csrf_token(self),
            'hash': self.record_portal._sign_token(self.partner_2.id),
            'message': 'Test',
            'pid': self.partner_2.id,
            'redirect': '/',
            'res_model': self.record_portal._name,
            'res_id': self.record_portal.id,
            'token': self.record_portal.access_token,
        }

        # test as not logged
        self.url_open(url=post_url, data=post_data)
        message = self.record_portal.message_ids[0]

        self.assertIn('Test', message.body)
        self.assertEqual(message.author_id, self.partner_2)
