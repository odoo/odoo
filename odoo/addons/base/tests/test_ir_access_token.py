from datetime import datetime, timedelta

from freezegun import freeze_time
from functools import partial

from odoo.exceptions import AccessError, ValidationError
from odoo.sql_db import BaseCursor
from odoo.tests.common import new_test_user, TransactionCase


class TestIrAccessToken(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.enterClassContext(cls.registry_test_mode())

        cls.IrAccessToken = cls.env['ir.access.token']

        cls.admin = new_test_user(cls.env, 'Test Admin', groups='base.group_erp_manager')
        cls.user_1 = new_test_user(cls.env, 'Test User 1')
        cls.user_2 = new_test_user(cls.env, 'Test User 2')

        cls.Partner = cls.env['res.partner'].with_user(cls.admin)
        cls.partner = cls.Partner.create({'name': 'Test partner_sudo'})

        cls.PartnerSudo = cls.Partner.sudo()
        cls.partner_sudo = cls.partner.sudo()

        cls.classPatch(BaseCursor, 'now', lambda cr: datetime.now())

        cls.IrAccessToken.search([]).unlink()

    def test_grant_access_to_record(self):
        with self.assertRaises(AssertionError):  # Sudo environment required to grant access tokens
            self.partner._grant_access_token('test.partner_phone_number_read')

        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        self.assertTrue(token, 'An access token must be generated and returned')

        with self.assertRaises(AssertionError):  # Sudo environment required to retrieve partner_sudos
            self.Partner._get_sudo_record_from_access_token('test.partner_phone_number_read', token)

        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo, self.partner_sudo, 'The partner_sudo must be found')

    def test_grant_access_to_record_with_manual_token(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', _manual_token='123456789')
        self.assertEqual(token, '123456789', 'The raw access token must be returned')

        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', '123456789', record=self.partner_sudo)
        self.assertEqual(partner_sudo, self.partner_sudo, 'The partner_sudo must be found')

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_duration(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', duration=timedelta(days=10))

        with freeze_time('2026-01-09'):
            partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
            self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')

        with freeze_time('2026-01-11'), self.assertRaises(AccessError):  # The token is invalid
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)

    @freeze_time('2026-01-01')
    def test_grant_access_to_record_with_expiration_in_past(self):
        with self.assertRaises(ValidationError):
            self.partner_sudo._grant_access_token('test.partner_phone_number_read', duration=timedelta(days=-1))

    def test_grant_access_to_record_with_owner(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', owner=self.user_1)

        with self.assertRaises(AccessError):  # With user 2, the token is invalid
            self.PartnerSudo.with_user(self.user_2).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token)

        partner_sudo = self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token is valid for the owner user_1')

    def test_grant_access_to_record_with_scope(self):
        token_read = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        token_write = self.partner_sudo._grant_access_token('test.partner_phone_number_write')

        with self.assertRaises(AccessError):  # Token incorrect for the scope
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_write', token_read)
        with self.assertRaises(AccessError):  # Token incorrect for the scope
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_write)

        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_write', token_write)
        self.assertEqual(partner_sudo, self.partner_sudo)
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_read)
        self.assertEqual(partner_sudo, self.partner_sudo)

    @freeze_time('2026-01-01')
    def test_ensure_database_integrity_expiration(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', duration=timedelta(days=10))

        with freeze_time('2026-01-09'):
            partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
            self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
            # Alter DB - Attempting to extend a token
            access_token = self.IrAccessToken.search([], limit=1)
            self.env.registry['base'].write(access_token, {'expiration': datetime(2026, 1, 20)})  # Bypass write override
            with self.assertRaises(AccessError):  # We detect a modification in the expiration
                self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)

    def test_ensure_database_integrity_owner(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', owner=self.user_1)
        partner_sudo = self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
        # Alter DB - Attempting to change user
        access_token = self.IrAccessToken.search([], limit=1)
        self.env.registry['base'].write(access_token, {'owner_id': self.user_2})  # Bypass write override
        with self.assertRaises(AccessError):  # We detect a modification in the user
            self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        with self.assertRaises(AccessError):  # Token completely invalid (even if we use the updated user)
            self.PartnerSudo.with_user(self.user_2).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token)

    def test_ensure_database_integrity_scope(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
        # Alter DB - Attempting to change scope
        access_token = self.IrAccessToken.search([], limit=1)
        self.env.registry['base'].write(access_token, {'scope': 'test.partner_phone_number_write'})  # Bypass write override
        with self.assertRaises(AccessError):  # We detect a modification in the scope
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        with self.assertRaises(AccessError):  # Token completely invalid (even if we use the updated scope)
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_write', token)

    def test_revoke_access_to_record(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo, self.partner_sudo)

        with self.assertRaises(AssertionError):  # Sudo environment required to revoke access tokens
            self.partner._revoke_access_tokens('test.partner_phone_number_read')
        self.partner_sudo._revoke_access_tokens('test.partner_phone_number_read')

        with self.assertRaises(AccessError):  # The token is invalid
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)

    def test_revoke_access_to_record_scope(self):
        token_read = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        token_write = self.partner_sudo._grant_access_token('test.partner_phone_number_write')

        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_read)
        self.assertEqual(partner_sudo, self.partner_sudo)
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_write', token_write)
        self.assertEqual(partner_sudo, self.partner_sudo)

        self.partner_sudo._revoke_access_tokens('test.partner_phone_number_write')

        with self.assertRaises(AccessError):  # The token is invalid
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_write', token_write)

        self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_read)
        self.assertEqual(partner_sudo, self.partner_sudo)

    def test_revoke_access_to_record_scope_concurrent(self):
        token_1 = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        token_2 = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')

        self.partner_sudo._revoke_access_tokens('test.partner_phone_number_read')
        with self.assertRaises(AccessError):
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
        with self.assertRaises(AccessError):
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)

    def test_revoke_access_to_record_according_user(self):
        token_1 = self.partner_sudo._grant_access_token('test.partner_phone_number_read', owner=self.user_1)
        token_2 = self.partner_sudo._grant_access_token('test.partner_phone_number_read', owner=self.user_2)
        partner_sudo = self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
        partner_sudo = self.PartnerSudo.with_user(self.user_2).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')

        self.partner_sudo._revoke_access_tokens('test.partner_phone_number_read', owners=self.user_1)
        with self.assertRaises(AccessError):
            self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
        partner_sudo = self.PartnerSudo.with_user(self.user_2).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must always be valid')

    def test_revoke_access_to_record_according_share(self):
        token_shared = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        token_user = self.partner_sudo._grant_access_token('test.partner_phone_number_read', owner=self.user_1)
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_shared)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
        partner_sudo = self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token_user)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')

        self.partner_sudo._revoke_access_tokens('test.partner_phone_number_read', revoke_shared=True)
        with self.assertRaises(AccessError):
            self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_shared)
        partner_sudo = self.PartnerSudo.with_user(self.user_1).sudo()._get_sudo_record_from_access_token('test.partner_phone_number_read', token_user)
        self.assertEqual(partner_sudo, self.partner_sudo, 'Token must always be valid')

    @freeze_time('2026-01-01')
    def test_invalidate_concurrent_tokens_according_expiration(self):
        token_1 = self.partner_sudo._grant_access_token('test.partner_phone_number_read', duration=timedelta(days=10))
        token_2 = self.partner_sudo._grant_access_token('test.partner_phone_number_read', duration=timedelta(days=20))

        with freeze_time('2026-01-05'):
            partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
            self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')
            partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)
            self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')

        with freeze_time('2026-01-15'):
            with self.assertRaises(AccessError):
                self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
            partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)
            self.assertEqual(partner_sudo, self.partner_sudo, 'Token must be valid')

        with freeze_time('2026-01-25'):
            with self.assertRaises(AccessError):
                self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_1)
            with self.assertRaises(AccessError):
                self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token_2)

    def test_retrieve_record_from_concurrent_token(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        self.partner_sudo._grant_access_token('test.partner_phone_number_read')
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo, self.partner_sudo)

        # Using manual token
        # search domain does not use the access token ID, so filtering must be performed
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', _manual_token='123456789')
        self.partner_sudo._grant_access_token('test.partner_phone_number_read', _manual_token='abcdefghi')
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token, record=self.partner_sudo)
        self.assertEqual(partner_sudo, self.partner_sudo)

    def test_place_extra_information_in_token(self):
        token = self.partner_sudo._grant_access_token('test.partner_phone_number_read', extra=self.partner_sudo.id)
        partner_sudo = self.PartnerSudo._get_sudo_record_from_access_token('test.partner_phone_number_read', token)
        self.assertEqual(partner_sudo.env.context['access_token_extra'], self.partner_sudo.id)

        # Try to use a non-serializable object
        with self.assertRaises(TypeError):
            self.partner_sudo._grant_access_token('test.partner_phone_number_read', extra={self.partner_sudo.id})

    def test_falsy_extra_information_in_token(self):
        grant_token = partial(self.partner_sudo._grant_access_token, 'test.partner_phone_number_read')

        def get_context_extra(token):
            return self.PartnerSudo._get_sudo_record_from_access_token(
                'test.partner_phone_number_read', token
            ).env.context['access_token_extra']

        token_empty = grant_token()
        token_none = grant_token(extra=None)
        token_false = grant_token(extra=False)
        token_0 = grant_token(extra=0)
        token_empty_str = grant_token(extra='')

        self.assertIsNone(get_context_extra(token_empty))
        self.assertIsNone(get_context_extra(token_none))
        self.assertIs(get_context_extra(token_false), False)
        self.assertEqual(get_context_extra(token_0), 0)
        self.assertEqual(get_context_extra(token_empty_str), '')
