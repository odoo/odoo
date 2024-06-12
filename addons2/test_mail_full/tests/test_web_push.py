# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import socket
from datetime import datetime

import odoo
from odoo.tools.misc import mute_logger
from odoo.addons.mail.models.partner_devices import InvalidVapidError
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.tests import tagged
from markupsafe import Markup
from unittest.mock import patch
from types import SimpleNamespace


@tagged('post_install', '-at_install', 'mail_push')
class TestWebPushNotification(SMSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        channel = cls.env['discuss.channel'].with_context(cls._test_context)

        cls.user_email = cls.user_employee
        cls.user_email.notification_type = 'email'

        cls.user_inbox = mail_new_test_user(
            cls.env, login='user_inbox', groups='base.group_user', name='User Inbox',
            notification_type='inbox'
        )

        cls.record_simple = cls.env['mail.test.simple'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com'
        })
        cls.record_simple.message_subscribe(partner_ids=[
            cls.user_email.partner_id.id,
            cls.user_inbox.partner_id.id,
        ])

        cls.direct_message_channel = channel.with_user(cls.user_email).create({
            'channel_partner_ids': [
                (4, cls.user_email.partner_id.id),
                (4, cls.user_inbox.partner_id.id),
            ],
            'channel_type': 'chat',
            'name': 'Direct Message',
        })

        cls.group_channel = cls.env['discuss.channel'].channel_create(name='Channel', group_id=None)
        cls.group_channel.add_members((cls.user_email + cls.user_inbox).partner_id.ids)

        cls.env['mail.partner.device'].get_web_push_vapid_public_key()

        cls.vapid_public_key = cls.env['mail.partner.device'].get_web_push_vapid_public_key()

        cls.env['mail.partner.device'].sudo().create([{
            'endpoint': 'https://test.odoo.com/webpush/user1',
            'expiration_time': None,
            'keys': json.dumps({
                'p256dh': 'BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A',
                'auth': 'DJFdtAgZwrT6yYkUMgUqow'
            }),
            'partner_id': cls.user_email.partner_id.id,
        }])

        cls.env['mail.partner.device'].sudo().create([{
            'endpoint': 'https://test.odoo.com/webpush/user2',
            'expiration_time': None,
            'keys': json.dumps({
                'p256dh': 'BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A',
                'auth': 'DJFdtAgZwrT6yYkUMgUqow'
            }),
            'partner_id': cls.user_inbox.partner_id.id,
        }])

    def _trigger_cron_job(self):
        self.env.ref('mail.ir_cron_web_push_notification').method_direct_trigger()

    def _assert_notification_count_for_cron(self, number_of_notification):
        notification_count = self.env['mail.notification.web.push'].search_count([])
        self.assertEqual(notification_count, number_of_notification)

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    def test_push_notifications(self, push_to_end_point):
        # Test No Inbox Condition
        self.record_simple.with_user(self.user_inbox).message_notify(
            partner_ids=self.user_email.partner_id.ids,
            body='Test',
            subject='Test Activity',
            record_name=self.record_simple._name,
        )

        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_not_called()


        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body='Test message send via Web Push',
            subject='Test Activity',
            record_name=self.record_simple._name,
        )

        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
        self.assertIn(self.record_simple._name, payload_value['title'])
        self.assertIn(self.user_email.name, payload_value['title'])
        self.assertEqual(payload_value['options']['body'], 'Test message send via Web Push')
        self.assertEqual(payload_value['options']['data']['res_id'], self.record_simple.id)
        self.assertEqual(payload_value['options']['data']['model'], self.record_simple._name)
        self.assertIn('icon', payload_value['options'])
        self.assertIn('res.partner', payload_value['options']['icon'])
        self.assertEqual(push_to_end_point.call_args.kwargs['device']['endpoint'], 'https://test.odoo.com/webpush/user2')
        self.assertIn('vapid_private_key', push_to_end_point.call_args.kwargs)
        self.assertIn('vapid_public_key', push_to_end_point.call_args.kwargs)

        # Reset the mock counter
        push_to_end_point.reset_mock()

        # Test Tracking Message
        mail_test_ticket = self.env['mail.test.ticket'].with_context(self._test_context)
        record_full = mail_test_ticket.with_user(self.user_email).create({
            'name': 'Test',
        })
        record_full = record_full.with_context(mail_notrack=False)

        container = self.env['mail.test.container'].create({'name': 'Container'})
        record_full.message_subscribe(
            partner_ids=[self.user_email.partner_id.id],
            subtype_ids=[self.env.ref('test_mail.st_mail_test_ticket_container_upd').id],
        )
        record_full.write({
            'name': 'Test2',
            'email_from': 'noone@example.com',
            'container_id': container.id,
        })
        self.flush_tracking()
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_not_called()

        container2 = self.env['mail.test.container'].create({'name': 'Container Two'})
        record_full.message_subscribe(
            partner_ids=[self.user_inbox.partner_id.id],
            subtype_ids=[self.env.ref('test_mail.st_mail_test_ticket_container_upd').id],
        )
        record_full.write({
            'name': 'Test3',
            'email_from': 'noone@example.com',
            'container_id': container2.id,
        })
        self.flush_tracking()
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
        # As the tracking values are converted to text. We check the '→' added by ocn_client.
        self.assertIn('→', payload_value['options']['body'], 'No Tracking Message found')

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    def test_push_notifications_all_type(self, push_to_end_point):
        # Test Direct Message
        self.direct_message_channel.with_user(self.user_email).message_post(
            body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')

        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()
        self.assertEqual(push_to_end_point.call_args.kwargs['device']['endpoint'], 'https://test.odoo.com/webpush/user2')

        # Reset the mock counter
        push_to_end_point.reset_mock()

        # Test Direct Message with channel Muted
        self.env['discuss.channel.member'].search([
            ('partner_id', '=', self.user_inbox.partner_id.id),
            ('channel_id', '=', self.direct_message_channel.id),
        ]).write({
            'mute_until_dt': datetime(9999, 1, 1, 14, 00),
        })
        self.direct_message_channel.with_user(self.user_email).message_post(
            body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')

        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_not_called()

        # Reset the mock counter
        push_to_end_point.reset_mock()

        # Test Following Message
        self.record_simple.with_user(self.user_email).message_post(
            body='Test', message_type='comment', subtype_xmlid='mail.mt_comment'
        )
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()

        # Reset the mock counter
        push_to_end_point.reset_mock()

        # Test Channel Message
        self.group_channel.with_user(self.user_email).message_post(
            body='Test', partner_ids=self.user_inbox.partner_id.ids,
            message_type='comment', subtype_xmlid='mail.mt_comment')
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()

        # Reset the mock counter
        push_to_end_point.reset_mock()

        # Test AtMention Message
        self.record_simple.with_user(self.user_email).message_post(
            body=Markup('<a href="/web" data-oe-id="%i" data-oe-model="res.partner" >@user</a>') %
                 self.user_inbox.partner_id.id,
            message_type='comment', subtype_xmlid='mail.mt_comment'
        )
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    def test_push_notifications_mail_replay(self, push_to_end_point):
        test_record = self.env['mail.test.gateway'].with_context(self._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        })
        test_record.message_subscribe(partner_ids=[self.user_inbox.partner_id.id])

        fake_email = self.env['mail.message'].create({
            'model': 'mail.test.gateway',
            'res_id': test_record.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'author_id': self.user_email.partner_id.id,
            'message_id': '<123456-openerp-%s-mail.test.gateway@%s>' % (test_record.id, socket.gethostname()),
        })

        self.format_and_process(
            MAIL_TEMPLATE, self.user_email.email_formatted,
            self.user_inbox.email_formatted,
            subject='Test Subject Reply By mail',
            extra='In-Reply-To:\r\n\t%s\n' % fake_email.message_id,
        )
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
        self.assertIn(self.user_email.name, payload_value['title'])
        self.assertIn(
            'Please call me as soon as possible this afternoon!\n\n--\nSylvie',
            payload_value['options']['body'],
            'The body must contain the text send by mail'
        )

    @patch.object(odoo.addons.mail.models.web_push, 'push_to_end_point')
    def test_push_notifications_cron(self, push_to_end_point):
        # Add 4 more devices to force sending via cron queue
        for index in range(10, 14):
            self.env['mail.partner.device'].sudo().create([{
                'endpoint': 'https://test.odoo.com/webpush/user%d' % index,
                'expiration_time': None,
                'keys': json.dumps({
                    'p256dh': 'BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A',
                    'auth': 'DJFdtAgZwrT6yYkUMgUqow'
                }),
                'partner_id': self.user_inbox.partner_id.id,
            }])

        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body='Test message send via Web Push',
            subject='Test Activity',
            record_name=self.record_simple._name,
        )

        self._assert_notification_count_for_cron(5)
        # Force the execution of the cron
        self._trigger_cron_job()
        self.assertEqual(push_to_end_point.call_count, 5)

    @patch.object(odoo.addons.mail.models.mail_thread.Session, 'post',
                  return_value=SimpleNamespace(**{'status_code': 201, 'text': 'Ok'}))
    def test_push_notifications_encryption_simple(self, post):
        """
            Test to see if all parameters sent to the endpoint are present.
            This test doesn't test if the cryptographic values are correct.
        """
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body='Test message send via Web Push',
            subject='Test Activity',
            record_name=self.record_simple._name,
        )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], 'https://test.odoo.com/webpush/user2')
        self.assertIn('headers', post.call_args.kwargs)
        self.assertIn('vapid', post.call_args.kwargs['headers']['Authorization'])
        self.assertIn('t=', post.call_args.kwargs['headers']['Authorization'])
        self.assertIn('k=', post.call_args.kwargs['headers']['Authorization'])
        self.assertEqual('aes128gcm', post.call_args.kwargs['headers']['Content-Encoding'])
        self.assertEqual('0', post.call_args.kwargs['headers']['TTL'])
        self.assertIn('data', post.call_args.kwargs)
        self.assertIn('timeout', post.call_args.kwargs)

    @patch.object(odoo.addons.mail.models.mail_thread.Session, 'post',
                  return_value=SimpleNamespace(**{'status_code': 404, 'text': 'Device Unreachable'}))
    def test_push_notifications_device_unreachable(self, post):
        with mute_logger('odoo.addons.mail.web_push'):
            self.record_simple.with_user(self.user_email).message_notify(
                partner_ids=self.user_inbox.partner_id.ids,
                body='Test message send via Web Push',
                subject='Test Activity',
                record_name=self.record_simple._name,
            )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        # Test that the unreachable device is deleted from the DB
        notification_count = self.env['mail.partner.device'].search_count([('endpoint', '=', 'https://test.odoo.com/webpush/user2')])
        self.assertEqual(notification_count, 0)


    def test_push_notification_regenerate_vpaid_keys(self):
        ir_params_sudo = self.env['ir.config_parameter'].sudo()
        ir_params_sudo.search([('key', 'in', [
            'mail.web_push_vapid_private_key',
            'mail.web_push_vapid_public_key'
        ])]).unlink()
        new_vapid_public_key = self.env['mail.partner.device'].get_web_push_vapid_public_key()
        self.assertNotEqual(self.vapid_public_key, new_vapid_public_key)
        with self.assertRaises(InvalidVapidError):
            self.env['mail.partner.device'].register_devices(
                endpoint='https://test.odoo.com/webpush/user1',
                expiration_time=None,
                keys=json.dumps({
                    'p256dh': 'BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A',
                    'auth': 'DJFdtAgZwrT6yYkUMgUqow'
                }),
                partner_id=self.user_email.partner_id.id,
                vapid_public_key=self.vapid_public_key,
            )
