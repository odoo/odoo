import json
import socket

from datetime import datetime, timedelta

import odoo

from odoo.tools.misc import mute_logger
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.jwt import InvalidVapidError
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
        group_channel.add_members(guest_ids=[self.guest.id])

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
                channel_as_sender.message_post(
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

        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.user_email.email_formatted,
                f'{self.alias_gateway.display_name}, {self.user_inbox.email_formatted}',
                subject='Repy By Email',
                extra='In-Reply-To:\r\n\t%s\n' % test_record.message_ids.message_id,
            )
        self.assertPushNotification(
            mail_push_count=0, title_content=self.user_email.name,
            body_content='Please call me as soon as possible this afternoon!\n\n--\nSylvie',
        )

    @mute_logger('odoo.tests')
    def test_notify_by_push_message_notify(self):
        """ In case of notification, only inbox users are notified """
        for recipient, has_notification in [(self.user_email, False), (self.user_inbox, True)]:
            with self.subTest(recipient=recipient):
                with self.mock_mail_gateway():
                    self.record_simple.with_user(self.user_admin).message_notify(
                        body='Test Push Body',
                        partner_ids=recipient.partner_id.ids,
                        record_name=self.record_simple.display_name,
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
            record_name=self.record_simple._name,
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
                record_name=self.record_simple._name,
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
