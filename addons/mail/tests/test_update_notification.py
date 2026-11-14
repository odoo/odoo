# -*- coding: utf-8 -*-
from cryptography.hazmat.primitives.asymmetric import ed448
import json
from unittest.mock import patch

from odoo.addons.mail.models.update import _decode_key
from odoo.tests.common import TransactionCase


class TestUpdateNotification(TransactionCase):
    def test_user_count(self):
        ping_msg = self.env['publisher_warranty.contract'].with_context(active_test=False)._get_message()
        user_count = self.env['res.users'].search_count([('active', '=', True)])
        self.assertEqual(ping_msg.get('nbr_users'), user_count, 'Update Notification: Users count is badly computed in ping message')
        share_user_count = self.env['res.users'].search_count([('active', '=', True), ('share', '=', True)])
        self.assertEqual(ping_msg.get('nbr_share_users'), share_user_count, 'Update Notification: Portal Users count is badly computed in ping message')


class TestUpdateNotificationSignature(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.constant_warranty_message = {
            'dbuuid': 'some-uuid',
        }
        cls.ed25519_key = 'ed25519.a9NwA/4CYXBbSj089SgZpsW3emMPZrLpCVmFuU8yKSc='
        cls.ed25519_public_key = '8rFMjH65od5Gvor1c7XuyJYrtYhi3SZ2rGWo0qEYBw4='
        cls.ed25519_signature = 'iGqv4I+E4wIxPcI6ioXlcx6iaNeKHTChp/5WxzEANDsmHlnw9egz8RMKGvnVWnGlEWSY9f5vzvUOzWEhN0YtBw=='
        cls.ed448_key = 'ed448.cHt4SHflJ4dp40YSHPSZD01DXfD0vt7hX+UUUy6wdX7Dmkbj17qCRDQHUYOSQ8OQNvOm/53qL8DS'
        cls.ed448_public_key = 'tLT63brQaja/ASLCJ2xRxXMYty5WP1NX6nik8lgN0k/R2H4J8wR7aUX7grqytWMTEHaNCmUm6H4A'
        cls.ed448_signature = 'zBiFteCqdKiFnWUM6de5nMLKvYIPfUM9NH9bGLVQt30SM0E8gNIqR/t2Vdgwig6W/7WhveXWLfKAuO6jSDopq4hKkP93QM+XVFGndFiPgnNHyaq1+7J/7vz/DspzafnfupFLCvbWijcH/SYcIaXGAggA'

    def setUp(self):
        super().setUp()

        # Disable cursor creation and commit during these tests
        self.startPatcher(patch.object(
            self.env.registry['publisher_warranty.contract'].pool, 'cursor', **{
                'return_value.__enter__.return_value': self.env.cr,
                'return_value.__exit__.return_value': False,
            },
        ))
        self.startPatcher(patch.object(self.env.cr, 'commit', return_value=False))

        # Generation always returns a known key
        self.generate_privkey = self.startPatcher(patch(
            'odoo.addons.mail.models.update.ed25519.Ed25519PrivateKey.generate',
            return_value=_decode_key(self.ed25519_key),
        ))

        # Mock what Odoo returns
        self.update_requests_post = self.startPatcher(patch(
            'odoo.addons.mail.models.update.requests.post',
            **{'return_value.text': '{}'},
        ))

        # Simulate support for an old algorithm
        self.startPatcher(patch.dict(
            'odoo.addons.mail.models.update.PRIVATE_KEY_FACTORIES',
            {'ed448': ed448.Ed448PrivateKey},
        ))

        # Always return a known message
        self.startPatcher(patch.object(
            self.env.registry['publisher_warranty.contract'], '_get_message',
            side_effect=lambda: dict(self.constant_warranty_message),
        ))

    def test_initial_key_is_created_on_the_fly(self):
        ICP = self.env['ir.config_parameter'].sudo()
        self.assertFalse(ICP.get_param('database.update_notification.key'))
        self.assertFalse(ICP.get_param('database.update_notification.previous_key'))

        self.env['publisher_warranty.contract']._get_sys_logs()

        self.generate_privkey.assert_called_once_with()
        self.assertEqual(ICP.get_param('database.update_notification.key'), self.ed25519_key)
        self.assertFalse(ICP.get_param('database.update_notification.previous_key'))

    def test_existing_key_is_reused(self):
        ICP = self.env["ir.config_parameter"].sudo()

        self.env["publisher_warranty.contract"]._get_sys_logs()
        self.assertEqual(ICP.get_param("database.update_notification.key"), self.ed25519_key)

        self.env["publisher_warranty.contract"]._get_sys_logs()
        self.assertEqual(ICP.get_param("database.update_notification.key"), self.ed25519_key)

        self.generate_privkey.assert_called_once_with()
        self.assertEqual(self.update_requests_post.call_count, 2)

    def test_initial_key_is_used_for_signature(self):
        self.env['publisher_warranty.contract']._get_sys_logs()

        self.update_requests_post.assert_called_once()
        message = json.loads(self.update_requests_post.call_args.kwargs['data']['arg0'])
        self.assertEqual(message['signature'], {
            'algorithm': 'ed25519',
            'public_key': self.ed25519_public_key,
            'signature': self.ed25519_signature,
        })
        self.assertNotIn('old_signature', message)

    def test_algorithm_migration_rotates_old_key_and_creates_new_key(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('database.update_notification.key', self.ed448_key)

        self.env['publisher_warranty.contract']._get_sys_logs()

        self.generate_privkey.assert_called_once_with()
        self.update_requests_post.assert_called_once()
        message = json.loads(self.update_requests_post.call_args.kwargs['data']['arg0'])
        self.assertEqual(message['signature'], {
            'algorithm': 'ed25519',
            'public_key': self.ed25519_public_key,
            'signature': self.ed25519_signature,
        })
        self.assertEqual(message['old_signature'], {
            'algorithm': 'ed448',
            'public_key': self.ed448_public_key,
            'signature': self.ed448_signature,
        })
        self.assertEqual(ICP.get_param('database.update_notification.key'), self.ed25519_key)
        self.assertEqual(ICP.get_param('database.update_notification.previous_key'), self.ed448_key)

    def test_rotation_is_retryable_if_http_request_doesnt_acknowledge_new_key(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('database.update_notification.key', self.ed25519_key)
        ICP.set_param('database.update_notification.previous_key', self.ed448_key)

        self.env['publisher_warranty.contract']._get_sys_logs()

        self.generate_privkey.assert_not_called()
        self.update_requests_post.assert_called_once()
        message = json.loads(self.update_requests_post.call_args.kwargs['data']['arg0'])
        self.assertEqual(message['signature'], {
            'algorithm': 'ed25519',
            'public_key': self.ed25519_public_key,
            'signature': self.ed25519_signature,
        })
        self.assertEqual(message['old_signature'], {
            'algorithm': 'ed448',
            'public_key': self.ed448_public_key,
            'signature': self.ed448_signature,
        })
        self.assertEqual(ICP.get_param('database.update_notification.key'), self.ed25519_key)
        self.assertEqual(ICP.get_param('database.update_notification.previous_key'), self.ed448_key)

    def test_successful_rotation_removes_previous_key(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('database.update_notification.key', self.ed25519_key)
        ICP.set_param('database.update_notification.previous_key', self.ed448_key)

        self.update_requests_post.return_value.text = repr({
            'signature_key': 'f2b14c8c7eb9a1de46be8af573b5eec8962bb58862dd2676ac65a8d2a118070e',
        })
        self.env['publisher_warranty.contract']._get_sys_logs()

        self.assertEqual(ICP.get_param('database.update_notification.key'), self.ed25519_key)
        self.assertFalse(ICP.get_param('database.update_notification.previous_key'))
