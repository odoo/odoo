# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError
from odoo.sql_db import BaseCursor
from odoo.tests.common import new_test_user, TransactionCase


class TestIrAccessToken(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrAccessToken = cls.env['ir.access.token']

        cls.admin = new_test_user(cls.env, 'Test Admin', groups='base.group_erp_manager')
        cls.user_1 = new_test_user(cls.env, 'Test User 1')
        cls.user_2 = new_test_user(cls.env, 'Test User 2')

        cls.model = cls.env['res.partner'].sudo(False)
        cls.record = cls.model.create({'name': 'Test Record'}).sudo(False)

        cls.classPatch(BaseCursor, 'now', lambda cr: datetime.now())

    def setUp(self):
        super().setUp()
        self.IrAccessToken.search([]).unlink()

    def test_grant_access_to_record(self):
        with self.assertRaises(AccessError):  # Only administrators can grant access tokens
            self.record.with_user(self.user_1).grant_access_token('access-record')

        token = self.record.with_user(self.admin).grant_access_token('access-record')
        self.assertTrue(token, 'An access token must be generated and returned')

        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
        self.assertEqual(record, self.record, 'The record must be found')

    def test_grant_access_to_record_with_manual_token(self):
        token = self.record.with_user(self.admin).grant_access_token('access-record', _manual_token='123456789')
        self.assertEqual(token, '123456789', 'The raw access token must be returned')

        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', '123456789', record_id=self.record.id)
        self.assertEqual(record, self.record, 'The record must be found')

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_expiration(self):
        expiration = datetime(2026, 1, 10)
        token = self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration)

        with freeze_time('2026-01-9'):
            record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-11'), self.assertRaises(AccessError):  # The token is invalid
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_duration(self):
        duration = timedelta(days=10)
        token = self.record.with_user(self.admin).grant_access_token('access-record', expiration=duration)

        with freeze_time('2026-01-9'):
            record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-11'), self.assertRaises(AccessError):  # The token is invalid
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_expiration_in_past(self):
        expiration = datetime(2025, 1, 1)
        with self.assertRaises(ValidationError):
            self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration)

    def test_grant_access_to_record_with_owner(self):
        token = self.record.with_user(self.admin).grant_access_token('access-record', owner=self.user_1)

        with self.assertRaises(AccessError):  # With user 2, the token is invalid
            self.model.with_user(self.user_2).get_record_from_access_token('access-record', token)

        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
        self.assertEqual(record, self.record, 'Token is valid for the owner user_1')

    def test_grant_access_to_record_with_scope(self):
        token_read = self.record.with_user(self.admin).grant_access_token('access-read')
        token_write = self.record.with_user(self.admin).grant_access_token('access-write')

        with self.assertRaises(AccessError):  # Token incorrect for the scope
            self.model.with_user(self.user_1).get_record_from_access_token('access-write', token_read)
        with self.assertRaises(AccessError):  # Token incorrect for the scope
            self.model.with_user(self.user_1).get_record_from_access_token('access-read', token_write)

        record = self.model.with_user(self.user_1).get_record_from_access_token('access-write', token_write)
        self.assertTrue(record, self.record)
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-read', token_read)
        self.assertTrue(record, self.record)

    def test_revoke_access_to_record(self):
        token = self.record.with_user(self.admin).grant_access_token('access-record')
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
        self.assertEqual(record, self.record)

        with self.assertRaises(AccessError):  # Only administrators can revoke access tokens
            self.record.with_user(self.user_1).revoke_access_tokens('access-record')
        self.record.with_user(self.admin).revoke_access_tokens('access-record')

        with self.assertRaises(AccessError):  # The token is invalid
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)

    @freeze_time('2026-01-01')
    def test_ensure_database_integrity_expiration(self):
        expiration = datetime(2026, 1, 10)
        token = self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration)

        with freeze_time('2026-01-9'):
            record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
            self.assertEqual(record, self.record, 'Token must be valid')
            # Alter DB - Attempting to extend a token
            access_token = self.IrAccessToken.search([], limit=1)
            self.env.registry['base'].write(access_token, {'expiration': datetime(2026, 1, 20)})  # Bypass write override
            with self.assertRaises(AccessError):  # We detect a modification in the expiration
                self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)

    def test_ensure_database_integrity_owner(self):
        token = self.record.with_user(self.admin).grant_access_token('access-record', owner=self.user_1)
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
        self.assertEqual(record, self.record, 'Token must be valid')
        # Alter DB - Attempting to change user
        access_token = self.IrAccessToken.search([], limit=1)
        self.env.registry['base'].write(access_token, {'owner_id': self.user_2})  # Bypass write override
        with self.assertRaises(AccessError):  # We detect a modification in the user
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token)
        with self.assertRaises(AccessError):  # Token completly invalid (even if we use the updated user)
            self.model.with_user(self.user_2).get_record_from_access_token('access-record', token)

    def test_ensure_database_integrity_scope(self):
        token = self.record.with_user(self.admin).grant_access_token('access-read')
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-read', token)
        self.assertEqual(record, self.record, 'Token must be valid')
        # Alter DB - Attempting to change scope
        access_token = self.IrAccessToken.search([], limit=1)
        self.env.registry['base'].write(access_token, {'scope': 'access-write'})  # Bypass write override
        with self.assertRaises(AccessError):  # We detect a modification in the scope
            self.model.with_user(self.user_1).get_record_from_access_token('access-read', token)
        with self.assertRaises(AccessError):  # Token completly invalid (even if we use the updated scope)
            self.model.with_user(self.user_1).get_record_from_access_token('access-write', token)

    def test_revoke_concurrent_tokens(self):
        token_1 = self.record.with_user(self.admin).grant_access_token('access-record')
        token_2 = self.record.with_user(self.admin).grant_access_token('access-record')
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
        self.assertEqual(record, self.record, 'Token must be valid')
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_2)
        self.assertEqual(record, self.record, 'Token must be valid')

        self.record.with_user(self.admin).revoke_access_tokens('access-record')
        with self.assertRaises(AccessError):
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
        with self.assertRaises(AccessError):
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_2)

    def test_revoke_concurrent_tokens_according_user(self):
        token_1 = self.record.with_user(self.admin).grant_access_token('access-record', owner=self.user_1)
        token_2 = self.record.with_user(self.admin).grant_access_token('access-record', owner=self.user_2)
        record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
        self.assertEqual(record, self.record, 'Token must be valid')
        record = self.model.with_user(self.user_2).get_record_from_access_token('access-record', token_2)
        self.assertEqual(record, self.record, 'Token must be valid')

        self.record.with_user(self.admin).revoke_access_tokens('access-record', owners=self.user_1)
        with self.assertRaises(AccessError):
            self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
        record = self.model.with_user(self.user_2).get_record_from_access_token('access-record', token_2)
        self.assertEqual(record, self.record, 'Token must always be valid')

    @freeze_time('2026-01-01')
    def test_invalidate_concurrent_tokens_according_expiration(self):
        expiration_1 = datetime(2026, 1, 10)
        token_1 = self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration_1)
        expiration_1 = datetime(2026, 1, 20)
        token_2 = self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration_1)

        with freeze_time('2026-01-05'):
            record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
            self.assertEqual(record, self.record, 'Token must be valid')
            record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_2)
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-15'):
            with self.assertRaises(AccessError):
                self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
            record = self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_2)
            self.assertEqual(record, self.record, 'Token must be valid')

        with freeze_time('2026-01-25'):
            with self.assertRaises(AccessError):
                self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_1)
            with self.assertRaises(AccessError):
                self.model.with_user(self.user_1).get_record_from_access_token('access-record', token_2)

    @freeze_time('2026-01-01')
    def test_retrieve_token_from_record(self):
        token = self.record.with_user(self.admin).grant_access_token('access-record')

        with self.assertRaises(AccessError):  # Only administrators can retrieve access tokens
            self.record.with_user(self.user_1).get_access_token('access-record')
        retrieved_token = self.record.with_user(self.admin).get_access_token('access-record')
        self.assertEqual(token, retrieved_token)

        self.assertFalse(self.record.with_user(self.admin).get_access_token('access-random-scope'))

        expiration_1 = datetime(2026, 1, 10)
        token_1 = self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration_1)
        expiration_2 = datetime(2026, 1, 20)
        token_2 = self.record.with_user(self.admin).grant_access_token('access-record', expiration=expiration_2)

        with freeze_time('2026-01-05'):
            retrieved_token = self.record.with_user(self.admin).get_access_token('access-record')
            self.assertEqual(token, retrieved_token, 'Expiration null must be retrieve first')
            # Invalidate the token with the null expiration
            self.IrAccessToken.search([('expiration', '=', False)]).unlink()
            retrieved_token = self.record.with_user(self.admin).get_access_token('access-record')
            self.assertEqual(token_2, retrieved_token, 'Latest expiration be retrieve first')
            # Invalidate the token with the latest expiry date
            self.IrAccessToken.search([], order='expiration desc', limit=1).unlink()
            retrieved_token = self.record.with_user(self.admin).get_access_token('access-record')
            self.assertEqual(token_1, retrieved_token)

        with freeze_time('2026-01-15'):
            self.assertFalse(self.record.with_user(self.admin).get_access_token('access-record'))

    def test_retrieve_record_from_concurrent_token(self):
        token = self.record.with_user(self.admin).grant_access_token('access-record')
        self.record.with_user(self.admin).grant_access_token('access-record')
        record = self.model.with_user(self.admin).get_record_from_access_token('access-record', token)
        self.assertEqual(record, self.record)

        # Using manual token
        # search domain does not use the access token ID, so filtering must be performed
        token = self.record.with_user(self.admin).grant_access_token('access-record', _manual_token='123456789')
        self.record.with_user(self.admin).grant_access_token('access-record', _manual_token='abcdefghi')
        record = self.model.with_user(self.admin).get_record_from_access_token('access-record', token, record_id=self.record.id)
        self.assertEqual(record, self.record)
