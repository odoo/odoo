from datetime import timedelta
from hashlib import sha256

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessDenied, AccessError, ValidationError
from odoo.fields import Command
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestResUsersApikeys(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="ak_user")
        cls.Apikeys = cls.env["res.users.apikeys"]

    def _generate(self, scope="rpc", hours=1):
        exp = fields.Datetime.now() + timedelta(hours=hours)
        return self.Apikeys.with_user(self.user)._generate(scope, "k", exp)

    def _cached_auth(self, key):
        self.env["res.users"]._check_uid_passwd_cached(
            self.user.id, key, sha256(key.encode()).hexdigest()
        )

    def test_check_credentials_valid(self):
        key = self._generate(scope="rpc")
        self.assertEqual(
            self.Apikeys._check_credentials(scope="rpc", key=key), self.user.id
        )

    def test_generate_refreshes_cached_user_keys(self):
        self.assertFalse(self.user.api_key_ids)
        self._generate()
        self.assertEqual(len(self.user.api_key_ids), 1)
        self._generate()
        self.assertEqual(len(self.user.api_key_ids), 2)

    def test_check_credentials_wrong_key(self):
        self._generate(scope="rpc")
        self.assertIsNone(self.Apikeys._check_credentials(scope="rpc", key="0" * 40))

    def test_check_credentials_empty_args_raise(self):
        with self.assertRaises(ValueError):
            self.Apikeys._check_credentials(scope="", key="x")
        with self.assertRaises(ValueError):
            self.Apikeys._check_credentials(scope="rpc", key="")

    def test_check_credentials_expired(self):
        key = self._generate(scope="rpc", hours=-1)
        self.assertIsNone(self.Apikeys._check_credentials(scope="rpc", key=key))

    def test_check_credentials_inactive_user(self):
        key = self._generate(scope="rpc")
        self.user.active = False
        self.env.flush_all()
        self.assertIsNone(self.Apikeys._check_credentials(scope="rpc", key=key))

    def test_expiration_date_system_bypass(self):
        self.Apikeys.sudo()._check_expiration_date(None)

    def test_expiration_date_required_for_non_system(self):
        with self.assertRaises(ValidationError):
            self.Apikeys.with_user(self.user)._check_expiration_date(None)

    def test_expiration_date_over_limit(self):
        too_far = fields.Datetime.now() + timedelta(days=3650)
        with self.assertRaises(ValidationError):
            self.Apikeys.with_user(self.user)._check_expiration_date(too_far)

    def test_gc_removes_expired_keys(self):
        valid = self._generate(scope="rpc", hours=1)
        expired = self._generate(scope="rpc", hours=-1)
        self.Apikeys._gc_user_apikeys()
        self.assertEqual(
            self.Apikeys._check_credentials(scope="rpc", key=valid), self.user.id
        )
        self.assertIsNone(self.Apikeys._check_credentials(scope="rpc", key=expired))

    def test_remove_other_users_key_raises(self):
        self._generate(scope="rpc")
        key_rec = self.Apikeys.sudo().search([("user_id", "=", self.user.id)], limit=1)
        other = new_test_user(self.env, login="ak_other")
        with self.assertRaises(AccessError):
            key_rec.with_user(other)._remove()

    def test_make_key_requires_internal_user(self):
        portal = new_test_user(self.env, login="ak_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self.env["res.users.apikeys.description"].with_user(
                portal
            ).check_access_generate_key()

    def test_generate_requires_internal_user(self):
        portal = new_test_user(
            self.env, login="ak_portal_gen", groups="base.group_portal"
        )
        exp = fields.Datetime.now() + timedelta(hours=1)
        with self.assertRaises(AccessError):
            self.Apikeys.with_user(portal)._generate("rpc", "k", exp)

    def test_check_credentials_scope_mismatch(self):
        key = self._generate(scope="scope_x")
        self.assertIsNone(self.Apikeys._check_credentials(scope="scope_y", key=key))

    def test_check_credentials_scope_match(self):
        key = self._generate(scope="scope_x")
        self.assertEqual(
            self.Apikeys._check_credentials(scope="scope_x", key=key), self.user.id
        )

    def test_check_credentials_null_scope_matches_any(self):
        exp = fields.Datetime.now() + timedelta(hours=1)
        key = self.Apikeys.with_user(self.user)._generate(None, "k", exp)
        self.assertEqual(
            self.Apikeys._check_credentials(scope="anything", key=key), self.user.id
        )

    def test_generate_stores_hash_not_plaintext(self):
        key = self._generate(scope="rpc")
        self.assertEqual(len(key), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in key))
        self.env.cr.execute(
            "SELECT index, key FROM res_users_apikeys WHERE user_id = %s",
            (self.user.id,),
        )
        index, stored_key = self.env.cr.fetchone()
        self.assertEqual(index, key[:8])
        self.assertNotEqual(stored_key, key)
        self.assertTrue(stored_key.startswith("$pbkdf2-sha512$"))

    def test_remove_invalidates_cached_credentials(self):
        exp = fields.Datetime.now() + timedelta(hours=1)
        key = self.Apikeys.with_user(self.user)._generate(None, "k", exp)
        self._cached_auth(key)
        self.Apikeys.sudo().search([("user_id", "=", self.user.id)])._remove()
        with self.assertRaises(AccessDenied):
            self._cached_auth(key)

    def test_api_key_ids_not_writable_through_self_service(self):
        exp = fields.Datetime.now() + timedelta(hours=1)
        victim = new_test_user(self.env, login="ak_victim")
        self.Apikeys.with_user(victim)._generate(None, "victim key", exp)
        victim_key = self.Apikeys.sudo().search([("user_id", "=", victim.id)])

        attacker = self.user.with_user(self.user)
        for command in (Command.delete(victim_key.id), Command.link(victim_key.id)):
            with self.assertRaises(AccessError):
                attacker.write({"api_key_ids": [command]})

        self.assertTrue(victim_key.exists(), "the victim's key was destroyed")
        self.assertEqual(victim_key.user_id, victim, "the victim's key was stolen")

    def test_gc_invalidates_cached_credentials(self):
        exp = fields.Datetime.now() + timedelta(hours=1)
        key = self.Apikeys.with_user(self.user)._generate(None, "k", exp)
        self._cached_auth(key)
        self.env.cr.execute(
            """
            UPDATE res_users_apikeys
            SET expiration_date = (now() at time zone 'utc') - interval '1 day'
            WHERE user_id = %s
            """,
            (self.user.id,),
        )
        self.Apikeys._gc_user_apikeys()
        with self.assertRaises(AccessDenied):
            self._cached_auth(key)

    def test_description_batch_create(self):
        Description = self.env["res.users.apikeys.description"].with_user(self.user)
        wizards = Description.create(
            [{"name": "a", "duration": "1"}, {"name": "b", "duration": "1"}]
        )
        self.assertEqual(len(wizards), 2)
        too_far = fields.Datetime.now() + timedelta(days=3650)
        with self.assertRaises(ValidationError):
            Description.create(
                [
                    {"name": "a", "duration": "1"},
                    {"name": "b", "duration": "-1", "expiration_date": too_far},
                ]
            )

    def test_check_credentials_persistent_key_never_expires(self):
        admin = self.env.ref("base.user_admin")
        key = self.Apikeys.with_user(admin)._generate("rpc", "persistent", None)
        self.assertEqual(
            self.Apikeys._check_credentials(scope="rpc", key=key),
            admin.id,
        )

    def test_key_expiration_is_reported_for_the_scope_it_was_issued_for(self):
        expiration = fields.Datetime.now() + timedelta(hours=1)
        key = self.Apikeys.with_user(self.user)._generate("rpc", "k", expiration)
        self.assertEqual(
            self.Apikeys._get_key_expiration(scope="rpc", key=key), expiration
        )
        self.assertIsNone(self.Apikeys._get_key_expiration(scope="other", key=key))
        self.assertIsNone(self.Apikeys._get_key_expiration(scope="rpc", key="0" * 40))

    def test_a_cached_key_stops_authenticating_when_it_expires(self):
        key = self._generate(hours=1)
        Users = self.env["res.users"]
        Users._check_uid_passwd(self.user.id, key)
        with freeze_time(fields.Datetime.now() + timedelta(hours=2)):
            with self.assertRaises(AccessDenied):
                Users._check_uid_passwd(self.user.id, key)
