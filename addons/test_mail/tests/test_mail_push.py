import json
import socket

from datetime import datetime, timedelta

import odoo

from odoo.tools.misc import mute_logger
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.jwt import InvalidVapidError
from odoo.addons.mail.tools.web_push import ENCRYPTION_BLOCK_OVERHEAD, ENCRYPTION_HEADER_SIZE
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
        cls.alias_gateway = cls.env['mail.alias'].create({
            'alias_contact': 'everyone',
            'alias_domain': cls.mail_alias_domain.id,
            'alias_model_id': cls.env['ir.model']._get_id('mail.test.gateway.company'),
            'alias_name': 'alias.gateway',
        })

        # generate keys and devices
        cls.vapid_public_key = cls.env['mail.push.device'].get_web_push_vapid_public_key()
        cls.env['mail.push.device'].sudo().create([
            {
                'endpoint': f'https://test.odoo.com/webpush/user{(idx + 1)}',
                'expiration_time': None,
                'keys': json.dumps({
                    'p256dh': 'BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A',
                    'auth': 'DJFdtAgZwrT6yYkUMgUqow'
                }),
                'partner_id': user.partner_id.id,
            } for idx, user in enumerate(cls.user_email + cls.user_inbox)
        ])

    def _trigger_cron_job(self):
        self.env.ref('mail.ir_cron_web_push_notification').method_direct_trigger()

    def _assert_notification_count_for_cron(self, number_of_notification):
        notification_count = self.env['mail.push'].search_count([])
        self.assertEqual(notification_count, number_of_notification)

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    @mute_logger('odoo.tests')
    def test_notify_by_push(self, push_to_end_point):
        """ When posting a comment, notify both inbox and people outside of Odoo
        aka email """
        self.record_simple.with_user(self.user_admin).message_post(
            body=Markup('<p>Hello</p>'),
            message_type='comment',
            partner_ids=(self.user_email + self.user_inbox).partner_id.ids,
            subtype_xmlid='mail.mt_comment',
        )
        # not using cron, as max 1 push notif -> direct send
        self._assert_notification_count_for_cron(0)
        # two recipients, comment notifies both inbox and email people
        self.assertEqual(push_to_end_point.call_count, 2)

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    def test_notify_by_push_channel(self, push_to_end_point):
        """ Test various use case with discuss.channel. Chat and group channels
        sends push notifications, channel not. """
        chat_channel, channel_channel, group_channel = self.env['discuss.channel'].with_user(self.user_email).create([
            {
                'channel_partner_ids': [
                    (4, self.user_email.partner_id.id),
                    (4, self.user_inbox.partner_id.id),
                ],
                'channel_type': channel_type,
                'name': f'{channel_type} Message' if channel_type != 'group' else '',
            } for channel_type in ['chat', 'channel', 'group']
        ])
        group_channel._add_members(guests=self.guest)

        for channel, sender, notification_count in zip(
            (chat_channel + channel_channel + group_channel + group_channel),
            (self.user_email, self.user_email, self.user_email, self.guest),
            (1, 0, 1, 2),
        ):
            with self.subTest(channel_type=channel.channel_type):
                if sender == self.guest:
                    channel_as_sender = channel.with_user(self.env.ref('base.public_user')).with_context(guest=sender)
                else:
                    channel_as_sender = channel.with_user(self.user_email)
                # sudo: discuss.channel - guest can post as sudo in a test (simulating RPC without using network)
                channel_as_sender.sudo().message_post(
                        body='Test Push',
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )
                self.assertEqual(push_to_end_point.call_count, notification_count)
                if notification_count > 0:
                    payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
                    if channel.channel_type == 'chat':
                        self.assertEqual(payload_value['title'], f'{self.user_email.name}')
                    elif channel.channel_type == 'group':
                        self.assertIn(self.user_email.name, payload_value['title'])
                        self.assertIn(self.user_inbox.name, payload_value['title'])
                        self.assertIn(self.guest.name, payload_value['title'])
                        self.assertNotIn("False", payload_value['title'])
                    else:
                        self.assertEqual(payload_value['title'], f'#{channel.name}')
                    icon = (
                        '/web/static/img/odoo-icon-192x192.png'
                        if sender == self.guest
                        else f'/web/image/res.partner/{self.user_email.partner_id.id}/avatar_128'
                    )
                    self.assertEqual(payload_value['options']['icon'], icon)
                    self.assertEqual(payload_value['options']['body'], 'Test Push')
                    self.assertEqual(payload_value['options']['data']['res_id'], channel.id)
                    self.assertEqual(payload_value['options']['data']['model'], channel._name)
                    self.assertEqual(push_to_end_point.call_args.kwargs['device']['endpoint'], 'https://test.odoo.com/webpush/user2')
                push_to_end_point.reset_mock()

        # Test Direct Message with channel muted -> should skip push notif
        now = datetime.now()
        self.env['discuss.channel.member'].search([
            ('partner_id', 'in', (self.user_email.partner_id + self.user_inbox.partner_id).ids),
            ('channel_id', 'in', (chat_channel + channel_channel + group_channel).ids),
        ]).write({
            'mute_until_dt': now + timedelta(days=5)
        })
        chat_channel.with_user(self.user_email).message_post(
            body='Test',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        push_to_end_point.assert_not_called()
        push_to_end_point.reset_mock()

        self.env["discuss.channel.member"].search([
            ("partner_id", "in", (self.user_email.partner_id + self.user_inbox.partner_id).ids),
            ("channel_id", "in", (chat_channel + channel_channel + group_channel).ids),
        ]).write({
            "mute_until_dt": False,
        })

        # Test Channel Message
        group_channel.with_user(self.user_email).message_post(
            body='Test',
            partner_ids=self.user_inbox.partner_id.ids,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        push_to_end_point.assert_called_once()

    @patch.object(odoo.addons.mail.models.mail_thread, "push_to_end_point")
    def test_notify_by_push_channel_with_channel_notifications_settings(self, push_to_end_point):
        """ Test various use case with the channel notification settings."""
        all_test_user = mail_new_test_user(
            self.env,
            login="all",
            name="all",
            email="all@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        mentions_test_user = mail_new_test_user(
            self.env,
            login="mentions",
            name="mentions",
            email="mentions@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        nothing_test_user = mail_new_test_user(
            self.env,
            login="nothing",
            name="nothing",
            email="nothing@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        all_test_user.res_users_settings_ids.write({"channel_notifications": "all"})
        nothing_test_user.res_users_settings_ids.write({"channel_notifications": "no_notif"})

        # generate devices
        self.env["mail.push.device"].sudo().create(
            [
                {
                    "endpoint": f"https://test.odoo.com/webpush/user{(idx + 20)}",
                    "expiration_time": None,
                    "keys": json.dumps(
                        {
                            "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                            "auth": "DJFdtAgZwrT6yYkUMgUqow",
                        }
                    ),
                    "partner_id": user.partner_id.id,
                }
                for idx, user in enumerate(all_test_user + mentions_test_user + nothing_test_user)
            ]
        )

        channel_channel = self.env["discuss.channel"].with_user(self.user_email).create(
            [
                {
                    "channel_partner_ids": [
                        (4, self.user_email.partner_id.id),
                        (4, all_test_user.partner_id.id),
                        (4, mentions_test_user.partner_id.id),
                        (4, nothing_test_user.partner_id.id),
                    ],
                    "channel_type": "channel",
                    "name": "channel",
                }
            ]
        )
        # normal messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_called_once()
        # all_test_user should be notified
        self.assertEqual(push_to_end_point.call_args.kwargs["device"]["endpoint"], "https://test.odoo.com/webpush/user20")
        push_to_end_point.reset_mock()

        # mention messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push @mentions",
            message_type="comment",
            partner_ids=(all_test_user + mentions_test_user + nothing_test_user).partner_id.ids,
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(push_to_end_point.call_count, 2)
        # all_test_user and mentions_test_user should be notified
        self.assertEqual(push_to_end_point.call_args_list[0].kwargs["device"]["endpoint"], "https://test.odoo.com/webpush/user20")
        self.assertEqual(push_to_end_point.call_args_list[1].kwargs["device"]["endpoint"], "https://test.odoo.com/webpush/user21")
        push_to_end_point.reset_mock()

        # muted channel
        now = datetime.now()
        self.env["discuss.channel.member"].search(
            [
                ("partner_id", "in", (all_test_user.partner_id + mentions_test_user.partner_id + nothing_test_user.partner_id).ids),
            ]
        ).write(
            {
                "mute_until_dt": now + timedelta(days=5),
            }
        )
        # normal messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_not_called()
        # mention messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_not_called()

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_notify_by_push_mail_gateway(self):
        """ Check mail gateway push notifications """
        with self.mock_mail_gateway():
            test_record = self.format_and_process(
                MAIL_TEMPLATE, self.user_email.email_formatted,
                f'{self.alias_gateway.display_name}, {self.user_inbox.email_formatted}',
                subject='Test Record Creation',
                target_model='mail.test.gateway.company',
            )
        self.assertEqual(len(test_record.message_ids), 1)
        self.assertEqual(test_record.message_partner_ids, self.user_email.partner_id)
        test_record.message_subscribe(partner_ids=[self.user_inbox.partner_id.id])

        for include_as_external, has_notif in ((False, True), (True, False)):
            with self.mock_mail_gateway():
                to = f'{self.alias_gateway.display_name}'
                if include_as_external:
                    to += f', {self.user_inbox.email_formatted}'
                self.format_and_process(
                    MAIL_TEMPLATE, self.user_email.email_formatted, to,
                    subject='Repy By Email',
                    extra=f'In-Reply-To:\r\n\t{test_record.message_ids[-1].message_id}\n',
                )
            if has_notif:
                # user_inbox is notified by Odoo, hence receives a push notification
                self.assertPushNotification(
                    mail_push_count=0, title_content=self.user_email.name,
                    body_content='Please call me as soon as possible this afternoon!\n\n--\nSylvie',
                )
            else:
                self.assertNoPushNotification()

    @mute_logger('odoo.tests')
    def test_notify_by_push_message_notify(self):
        """ In case of notification, only inbox users are notified """
        for recipient, has_notification in [(self.user_email, False), (self.user_inbox, True)]:
            with self.subTest(recipient=recipient):
                with self.mock_mail_gateway():
                    self.record_simple.with_user(self.user_admin).message_notify(
                        body='Test Push Body',
                        partner_ids=recipient.partner_id.ids,
                        subject='Test Push Notification',
                    )
                # not using cron, as max 1 push notif -> direct send
                self._assert_notification_count_for_cron(0)
                if has_notification:
                    self.assertPushNotification(
                        mail_push_count=0,
                        endpoint='https://test.odoo.com/webpush/user2', keys=('vapid_private_key', 'vapid_public_key'),
                        title=f'{self.user_admin.name}: {self.record_simple.display_name}',
                        body_content='Test Push Body',
                        options={
                            'data': {'model': self.record_simple._name, 'res_id': self.record_simple.id,},
                        },
                    )
                else:
                    self.assertNoPushNotification()

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    @mute_logger('odoo.tests')
    def test_notify_call_invitation(self, push_to_end_point):
        inviting_user = self.env['res.users'].sudo().create({'name': "Test User", 'login': 'test'})
        channel = self.env['discuss.channel'].with_user(inviting_user)._get_or_create_chat(
            partners_to=[self.user_email.partner_id.id])
        inviting_channel_member = channel.sudo().channel_member_ids.filtered(
            lambda channel_member: channel_member.partner_id == inviting_user.partner_id)

        inviting_channel_member._rtc_join_call()
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
        self.assertEqual(
            payload_value['title'],
            "Incoming call",
        )
        options = payload_value['options']
        self.assertTrue(options['requireInteraction'])
        self.assertEqual(options['body'], f"Conference: {channel.name}")
        self.assertEqual(options['actions'], [
            {
                "action": "DECLINE",
                "type": "button",
                "title": "Decline",
            },
            {
                "action": "ACCEPT",
                "type": "button",
                "title": "Accept",
            },
        ])
        data = options['data']
        self.assertEqual(data['type'], "CALL")
        self.assertEqual(data['res_id'], channel.id)
        self.assertEqual(data['model'], "discuss.channel")
        push_to_end_point.reset_mock()

        inviting_channel_member._rtc_leave_call()
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
        self.assertEqual(payload_value['options']['data']['type'], "CANCEL")
        push_to_end_point.reset_mock()

    @patch.object(odoo.addons.mail.models.mail_thread, 'push_to_end_point')
    def test_notify_by_push_tracking(self, push_to_end_point):
        """ Test tracking message included in push notifications """
        container_update_subtype = self.env.ref('test_mail.st_mail_test_ticket_container_upd')
        ticket = self.env['mail.test.ticket'].with_user(self.user_email).create({
            'name': 'Test',
        })
        ticket.message_subscribe(
            partner_ids=[self.user_email.partner_id.id],
            subtype_ids=[container_update_subtype.id],
        )

        container = self.env['mail.test.container'].create({'name': 'Container'})
        ticket.write({
            'name': 'Test2',
            'email_from': 'noone@example.com',
            'container_id': container.id,
        })
        self.flush_tracking()
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_not_called()

        container2 = self.env['mail.test.container'].create({'name': 'Container Two'})
        ticket.message_subscribe(
            partner_ids=[self.user_inbox.partner_id.id],
            subtype_ids=[container_update_subtype.id],
        )
        ticket.write({
            'name': 'Test3',
            'email_from': 'noone@example.com',
            'container_id': container2.id,
        })
        self.flush_tracking()
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs['payload'])
        self.assertIn(
            f'{container_update_subtype.description}\nContainer: {container.name} → {container2.name}',
            payload_value['options']['body'],
            'Tracking changes should be included in push notif payload'
        )

    @patch.object(odoo.addons.mail.models.mail_push, 'push_to_end_point')
    def test_push_notifications_cron(self, push_to_end_point):
        # Add 4 more devices to force sending via cron queue
        for index in range(10, 14):
            self.env['mail.push.device'].sudo().create([{
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
        )

        self._assert_notification_count_for_cron(5)
        # Force the execution of the cron
        self._trigger_cron_job()
        self.assertEqual(push_to_end_point.call_count, 5)

    @patch.object(odoo.addons.mail.models.mail_thread.Session, 'post',
                  return_value=SimpleNamespace(**{'status_code': 404, 'text': 'Device Unreachable'}))
    def test_push_notifications_error_device_unreachable(self, post):
        with mute_logger('odoo.addons.mail.tools.web_push'):
            self.record_simple.with_user(self.user_email).message_notify(
                partner_ids=self.user_inbox.partner_id.ids,
                body='Test message send via Web Push',
                subject='Test Activity',
            )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        # Test that the unreachable device is deleted from the DB
        notification_count = self.env['mail.push.device'].search_count([('endpoint', '=', 'https://test.odoo.com/webpush/user2')])
        self.assertEqual(notification_count, 0)

    @patch.object(odoo.addons.mail.models.mail_thread.Session, 'post',
                  return_value=SimpleNamespace(**{'status_code': 201, 'text': 'Ok'}))
    def test_push_notifications_error_encryption_simple(self, post):
        """ Test to see if all parameters sent to the endpoint are present.
        This test doesn't test if the cryptographic values are correct. """
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body='Test message send via Web Push',
            subject='Test Activity',
        )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], 'https://test.odoo.com/webpush/user2')
        self.assertIn('headers', post.call_args.kwargs)
        self.assertIn('vapid', post.call_args.kwargs['headers']['Authorization'])
        self.assertIn('t=', post.call_args.kwargs['headers']['Authorization'])
        self.assertIn('k=', post.call_args.kwargs['headers']['Authorization'])
        self.assertEqual('aes128gcm', post.call_args.kwargs['headers']['Content-Encoding'])
        self.assertEqual('60', post.call_args.kwargs['headers']['TTL'])
        self.assertIn('data', post.call_args.kwargs)
        self.assertIn('timeout', post.call_args.kwargs)

    def test_push_notification_regenerate_vapid_keys(self):
        ir_params_sudo = self.env['ir.config_parameter'].sudo()
        ir_params_sudo.search([('key', 'in', [
            'mail.web_push_vapid_private_key',
            'mail.web_push_vapid_public_key'
        ])]).unlink()
        new_vapid_public_key = self.env['mail.push.device'].get_web_push_vapid_public_key()
        self.assertNotEqual(self.vapid_public_key, new_vapid_public_key)
        with self.assertRaises(InvalidVapidError):
            self.env['mail.push.device'].register_devices(
                endpoint='https://test.odoo.com/webpush/user1',
                expiration_time=None,
                keys=json.dumps({
                    'p256dh': 'BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A',
                    'auth': 'DJFdtAgZwrT6yYkUMgUqow'
                }),
                partner_id=self.user_email.partner_id.id,
                vapid_public_key=self.vapid_public_key,
            )

    @patch.object(
        odoo.addons.mail.models.mail_thread.Session, 'post', return_value=SimpleNamespace(status_code=201, text='Ok')
    )
    @patch.object(
        odoo.addons.mail.models.mail_thread, 'push_to_end_point',
        wraps=odoo.addons.mail.tools.web_push.push_to_end_point,
    )
    def test_push_notifications_truncate_payload(self, thread_push_mock, session_post_mock):
        """Ensure that when we send large bodies with various character types,
        the final encrypted data (post-encryption) never exceeds 4096 bytes.

        This test checks the behavior for the current size limits and encryption overhead.
        See below test for a more illustrative example.
        See MailThread._truncate_payload for a more thorough explanation.

        Test scenarios include:
        - ASCII characters (X)
        - UTF-8 characters (Ø), at various offsets
        """
        # compute the size of an empty notification with these parameters
        # this could change based on the id of record_simple for example
        # but is otherwise constant for any notification sent with the same parameters
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body='',
            subject='Test Payload',
        )
        base_payload_size = len(thread_push_mock.call_args.kwargs['payload'].encode())
        effective_payload_size_limit = self.env['mail.thread']._truncate_payload_get_max_payload_length()
        # this is just a sanity check that the value makes sense, feel free to update as needed
        self.assertEqual(effective_payload_size_limit, 3993, "Payload limit should come out to 3990.")
        body_size_limit = effective_payload_size_limit - base_payload_size
        encryption_overhead = ENCRYPTION_HEADER_SIZE + ENCRYPTION_BLOCK_OVERHEAD

        test_cases = [
            # (description, body)
            ('empty string', '', 0, 0),
            ('1-byte ASCII characters (below limit)', 'X' * (body_size_limit - 1), body_size_limit - 1, body_size_limit - 1),
            ('1-byte ASCII characters (at limit)', 'X' * body_size_limit, body_size_limit, body_size_limit),
            ('1-byte ASCII characters (past limit)', 'X' * (body_size_limit + 1), body_size_limit, body_size_limit),
            ('1-byte ASCII characters (way past limit)', 'X' * 5000, body_size_limit, body_size_limit),
        ] + [  # \u00d8 check that it can be cut anywhere by offsetting the string by 1 byte each time
            (
                f'2-bytes UTF-8 characters (near limit + {offset}-byte offset)',
                ('+' * offset) + ('Ø' * (body_size_limit // 6)),
                offset + ((body_size_limit - offset) // 6),  # length truncated to nearest full character (\u00f8)
                offset * 1 + ((body_size_limit - offset) // 6) * 6,
            )
            for offset in range(0, 8)
        ]

        for description, body, expected_body_length, expected_body_size in test_cases:
            with self.subTest(description):
                self.record_simple.with_user(self.user_email).message_notify(
                    partner_ids=self.user_inbox.partner_id.ids,
                    body=body,
                    subject='Test Payload',
                )

                encrypted_payload = session_post_mock.call_args.kwargs['data']
                payload_before_encryption = thread_push_mock.call_args.kwargs['payload']
                self.assertLessEqual(
                    len(encrypted_payload), 4096, 'Final encrypted payload should not exceed 4096 bytes'
                )
                self.assertEqual(
                    len(json.loads(payload_before_encryption)['options']['body']), expected_body_length
                )
                self.assertEqual(
                    len(encrypted_payload),
                    base_payload_size + expected_body_size + encryption_overhead,
                    'Encrypted size should be exactly the base payload size + body size + encryption overhead.'
                )

    @patch.object(
        odoo.addons.mail.models.mail_thread.Session, 'post', return_value=SimpleNamespace(status_code=201, text='Ok')
    )
    @patch.object(
        odoo.addons.mail.models.mail_thread, 'push_to_end_point',
        wraps=odoo.addons.mail.tools.web_push.push_to_end_point,
    )
    @patch.object(
        odoo.addons.mail.tools.web_push, '_encrypt_payload',
        wraps=odoo.addons.mail.tools.web_push._encrypt_payload,
    )
    def test_push_notifications_truncate_payload_mocked_size_limit(self, web_push_encrypt_payload_mock, thread_push_mock, session_post_mock):
        """Illustrative test for text contents truncation.

        We want to ensure we truncate utf-8 values properly based on maximum payload size.
        Here max payload size is mocked, so that we can test on the same body each time to ease reading.

        See MailThread._truncate_payload for a more thorough explanation.
        """
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="",
            subject='Test Payload',
        )
        base_payload = thread_push_mock.call_args.kwargs['payload'].encode()
        base_payload_size = len(base_payload)
        encryption_overhead = ENCRYPTION_HEADER_SIZE + ENCRYPTION_BLOCK_OVERHEAD

        body = "BØDY"
        body_json = json.dumps(body)[1:-1]
        for size_limit, expected_body in [
            (base_payload_size + len(body_json), "BØDY"),
            (base_payload_size + len(body_json) - 1, "BØD"),
            (base_payload_size + len(body_json) - 2, "BØ"),
        ] + [  # truncating anywhere in \u00d8 (Ø) should truncate to the nearest full character (B)
            (base_payload_size + len(body_json) - n, "B")
            for n in range(3, 9)
        ] + [
            (base_payload_size + len(body_json) - 9, ""),
            (base_payload_size + len(body_json) - 10, ""),  # should still work even if it would still be too big after truncate
        ]:
            with self.subTest(size_limit=size_limit), patch.object(
                odoo.addons.mail.models.mail_thread.MailThread, '_truncate_payload_get_max_payload_length',
                return_value=size_limit,
            ):
                self.record_simple.with_user(self.user_email).message_notify(
                    partner_ids=self.user_inbox.partner_id.ids,
                    body=body,
                    subject='Test Payload',
                )
                payload_at_push = thread_push_mock.call_args.kwargs['payload']
                payload_before_encrypt = web_push_encrypt_payload_mock.call_args.args[0]
                encrypted_payload = session_post_mock.call_args.kwargs['data']
                self.assertEqual(payload_before_encrypt.decode(), payload_at_push, "Payload should not change between encryption and push call.")
                self.assertEqual(len(payload_before_encrypt), len(payload_at_push), "Encoded body should be same size as decoded.")
                self.assertEqual(
                    len(encrypted_payload), len(payload_before_encrypt) + encryption_overhead,
                    'Final encrypted payload should just be the size of the unencrypted payload + the size of encryption overhead.'
                )
                self.assertEqual(
                    json.loads(payload_at_push)['options']['body'], expected_body
                )
                if not expected_body:
                    self.assertEqual(
                        payload_before_encrypt, base_payload,
                        "Only the contents of the body should be truncated, not the rest of the payload."
                    )
