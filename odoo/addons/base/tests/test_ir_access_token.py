# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user, TransactionCase


class TestIrAccessToken(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrAccessToken = cls.env['ir.access.token']

        cls.admin = new_test_user(cls.env, 'Test Admin', groups='base.group_erp_manager')
        cls.user_1 = new_test_user(cls.env, 'Test User 1')
        cls.user_2 = new_test_user(cls.env, 'Test User 2')
        cls.record = cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

        cls.admin_user = cls.env.user.with_user(cls.admin)
        cls.user_1_user = cls.env.user.with_user(cls.user_1)
        cls.user_2_user = cls.env.user.with_user(cls.user_2)

    def setUp(self):
        super().setUp()
        self.IrAccessToken.search([]).unlink()

    def test_grant_access_to_record(self):
        with self.assertRaises(AccessError):  # Only administrators can grant access tokens
            self.user_1_user.grant_access_token(self.record, 'access-record')

        token = self.admin_user.grant_access_token(self.record, 'access-record')
        self.assertTrue(token, 'An access token must be generated and returned')

        record = self.user_1_user.use_access_token(token, 'access-record')
        self.assertEqual(record, self.record, 'The record must be found')

    def test_grant_access_to_record_with_value(self):
        token = self.admin_user.grant_access_token(self.record, 'access-record', value='123456789')
        self.assertEqual(token, '123456789', 'The raw access token must be returned')

        record = self.user_1_user.use_access_token('123456789', 'access-record')
        self.assertEqual(record, self.record, 'The record must be found')

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_expiration(self):
        expiration = datetime(2026, 1, 10)
        token = self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration)

        with freeze_time('2026-01-9'):
            record = self.user_1_user.use_access_token(token, 'access-record')
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-11'), self.assertRaises(AccessError):  # The token is invalid
            self.user_1_user.use_access_token(token, 'access-record')

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_expiration_in_past(self):
        expiration = datetime(2025, 1, 1)
        with self.assertRaises(ValidationError):
            self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration)

    def test_grant_access_to_record_with_owner(self):
        token = self.admin_user.grant_access_token(self.record, 'access-record', owner=self.user_1)

        with self.assertRaises(AccessError):  # With user 2, the token is invalid
            self.user_2_user.use_access_token(token, 'access-record')

        record = self.user_1_user.use_access_token(token, 'access-record')
        self.assertTrue(record, 'Token is valid for the owner user_1')

    def test_grant_access_to_record_with_scope(self):
        token_read = self.admin_user.grant_access_token(self.record, 'access-read')
        token_write = self.admin_user.grant_access_token(self.record, 'access-write')

        with self.assertRaises(AccessError):  # Token incorrect for the scope
            self.user_1_user.use_access_token(token_read, 'access-write')
        with self.assertRaises(AccessError):  # Token incorrect for the scope
            self.user_1_user.use_access_token(token_write, 'access-read')

        record = self.user_1_user.use_access_token(token_write, 'access-write')
        self.assertTrue(record, self.record)
        record = self.user_1_user.use_access_token(token_read, 'access-read')
        self.assertTrue(record, self.record)

    def test_revoke_access_to_record(self):
        token = self.admin_user.grant_access_token(self.record, 'access-record')
        record = self.user_1_user.use_access_token(token, 'access-record')
        self.assertEqual(record, self.record)

        with self.assertRaises(AccessError):  # Only administrators can revoke access tokens
            self.user_1_user.revoke_access_token(self.record, 'access-record')
        self.admin_user.revoke_access_token(self.record, 'access-record')

        with self.assertRaises(AccessError):  # The token is invalid
            self.user_1_user.use_access_token(token, 'access-record')

    @freeze_time('2026-01-01')
    def test_ensure_database_integrity_expiration(self):
        expiration = datetime(2026, 1, 10)
        token = self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration)

        with freeze_time('2026-01-9'):
            record = self.user_1_user.use_access_token(token, 'access-record')
            self.assertEqual(record, self.record, 'Token must be valid')
            # Alter DB - Attempting to extend a token
            access_token = self.IrAccessToken.search([], limit=1)
            self.env.registry['base'].write(access_token, {'expiration': datetime(2026, 1, 20)})  # Bypass write override
            with self.assertRaises(AccessError):  # We detect a modification in the expiration
                self.user_1_user.use_access_token(token, 'access-record')

    def test_ensure_database_integrity_owner(self):
        token = self.admin_user.grant_access_token(self.record, 'access-record', owner=self.user_1)
        record = self.user_1_user.use_access_token(token, 'access-record')
        self.assertEqual(record, self.record, 'Token must be valid')
        # Alter DB - Attempting to change user
        access_token = self.IrAccessToken.search([], limit=1)
        self.env.registry['base'].write(access_token, {'owner_id': self.user_2})  # Bypass write override
        with self.assertRaises(AccessError):  # We detect a modification in the user
            self.user_1_user.use_access_token(token, 'access-record')
        with self.assertRaises(AccessError):  # Token completly invalid (even if we use the updated user)
            self.user_2_user.use_access_token(token, 'access-record')

    def test_ensure_database_integrity_scope(self):
        token = self.admin_user.grant_access_token(self.record, 'access-read')
        record = self.user_1_user.use_access_token(token, 'access-read')
        self.assertEqual(record, self.record, 'Token must be valid')
        # Alter DB - Attempting to change scope
        access_token = self.IrAccessToken.search([], limit=1)
        self.env.registry['base'].write(access_token, {'scope': 'access-write'})  # Bypass write override
        with self.assertRaises(AccessError):  # We detect a modification in the scope
            self.user_1_user.use_access_token(token, 'access-read')
        with self.assertRaises(AccessError):  # Token completly invalid (even if we use the updated scope)
            self.user_1_user.use_access_token(token, 'access-write')

    def test_revoke_concurrent_tokens(self):
        token_1 = self.admin_user.grant_access_token(self.record, 'access-record')
        token_2 = self.admin_user.grant_access_token(self.record, 'access-record')
        record = self.user_1_user.use_access_token(token_1, 'access-record')
        self.assertEqual(record, self.record, 'Token must be valid')
        record = self.user_1_user.use_access_token(token_2, 'access-record')
        self.assertEqual(record, self.record, 'Token must be valid')

        self.admin_user.revoke_access_token(self.record, 'access-record')
        with self.assertRaises(AccessError):
            self.user_1_user.use_access_token(token_1, 'access-record')
        with self.assertRaises(AccessError):
            self.user_1_user.use_access_token(token_2, 'access-record')

    def test_revoke_concurrent_tokens_according_user(self):
        token_1 = self.admin_user.grant_access_token(self.record, 'access-record', owner=self.user_1)
        token_2 = self.admin_user.grant_access_token(self.record, 'access-record', owner=self.user_2)
        record = self.user_1_user.use_access_token(token_1, 'access-record')
        self.assertEqual(record, self.record, 'Token must be valid')
        record = self.user_2_user.use_access_token(token_2, 'access-record')
        self.assertEqual(record, self.record, 'Token must be valid')

        self.admin_user.revoke_access_token(self.record, 'access-record', owners=self.user_1)
        with self.assertRaises(AccessError):
            self.user_1_user.use_access_token(token_1, 'access-record')
        record = self.user_2_user.use_access_token(token_2, 'access-record')
        self.assertEqual(record, self.record, 'Token must always be valid')

    @freeze_time('2026-01-01')
    def test_invalidate_concurrent_tokens_according_expiration(self):
        expiration_1 = datetime(2026, 1, 10)
        token_1 = self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration_1)
        expiration_1 = datetime(2026, 1, 20)
        token_2 = self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration_1)

        with freeze_time('2026-01-05'):
            record = self.user_1_user.use_access_token(token_1, 'access-record')
            self.assertEqual(record, self.record, 'Token must be valid')
            record = self.user_1_user.use_access_token(token_2, 'access-record')
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-15'):
            with self.assertRaises(AccessError):
                self.user_1_user.use_access_token(token_1, 'access-record')
            record = self.user_1_user.use_access_token(token_2, 'access-record')
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-25'):
            with self.assertRaises(AccessError):
                self.user_1_user.use_access_token(token_1, 'access-record')
            with self.assertRaises(AccessError):
                self.user_1_user.use_access_token(token_2, 'access-record')

    @freeze_time('2026-01-01')
    def test_retrieve_token_from_record(self):
        token = self.admin_user.grant_access_token(self.record, 'access-record')

        with self.assertRaises(AccessError):  # Only administrators can retrieve access tokens
            self.user_1_user.retrieve_access_token(self.record, 'access-record')
        retrieved_token = self.admin_user.retrieve_access_token(self.record, 'access-record')
        self.assertEqual(token, retrieved_token)

        self.assertFalse(self.admin_user.retrieve_access_token(self.record, 'access-random-scope'))

        expiration_1 = datetime(2026, 1, 10)
        token_1 = self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration_1)
        expiration_1 = datetime(2026, 1, 20)
        token_2 = self.admin_user.grant_access_token(self.record, 'access-record', expiration=expiration_1)

        with freeze_time('2026-01-05'):
            retrieved_token = self.admin_user.retrieve_access_token(self.record, 'access-record')
            self.assertEqual(token, retrieved_token, 'Expiration null must be retrieve first')
            # Invalidate the token with the null expiration
            self.IrAccessToken.search([('expiration', '=', False)]).unlink()
            retrieved_token = self.admin_user.retrieve_access_token(self.record, 'access-record')
            self.assertEqual(token_2, retrieved_token, 'Latest expiration be retrieve first')
            # Invalidate the token with the latest expiry date
            self.IrAccessToken.search([], order='expiration desc', limit=1).unlink()
            retrieved_token = self.admin_user.retrieve_access_token(self.record, 'access-record')
            self.assertEqual(token_1, retrieved_token)

        with freeze_time('2026-01-15'):
            self.assertFalse(self.admin_user.retrieve_access_token(self.record, 'access-record'))

    def test_retrieve_token_from_record_create(self):
        retrieved_token = self.admin_user.retrieve_access_token(self.record, 'access-record', create=True)
        record = self.admin_user.use_access_token(retrieved_token, 'access-record')
        self.assertEqual(record, self.record)
