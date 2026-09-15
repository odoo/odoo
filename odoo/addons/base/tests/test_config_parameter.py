import os
from unittest.mock import patch

from cryptography.fernet import Fernet

import odoo
from odoo.exceptions import ConcurrencyError, ValidationError
from odoo.libs import sealing
from odoo.modules.registry import Registry
from odoo.tests import common
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import mute_logger
from odoo.tools.security import hmac

from odoo.addons.base.models.ir_config_parameter import _default_parameters


class TestIrConfigParameter(TransactionCase):
    def test_default_parameters(self):
        for key in _default_parameters:
            config_parameter = self.env["ir.config_parameter"].search(
                [("key", "=", key)], limit=1
            )
            with self.assertRaises(ValidationError):
                config_parameter.unlink()

            new_key = f"{key}_updated"
            with self.assertRaises(ValidationError):
                config_parameter.write({"key": new_key})


class TestSealedDatabaseSecret(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.real_key = {sealing.ENV_KEY: Fernet.generate_key().decode()}

    def _stored(self):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT value FROM ir_config_parameter WHERE key = 'database.secret'"
        )
        return self.env.cr.fetchone()[0]

    def _store_in_clear(self, value):
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_config_parameter SET value = %s WHERE key = 'database.secret'",
            [value],
        )
        self.env.invalidate_all()
        self.env.registry.clear_cache("stable")

    def test_with_a_key_the_secret_is_stored_sealed_and_read_in_clear(self):
        with patch.dict(os.environ, self.real_key):
            self.ICP.set_param("database.secret", "the-database-secret")

            self.assertTrue(sealing.is_sealed(self._stored()))
            self.assertNotIn("the-database-secret", self._stored())
            self.assertEqual(
                self.ICP.get_param("database.secret"), "the-database-secret"
            )

    def test_a_secret_left_in_clear_is_sealed_when_the_registry_loads(self):
        self._store_in_clear("legacy-secret")
        with patch.dict(os.environ, self.real_key):
            self.ICP._seal_sealed_parameters()

            self.assertTrue(sealing.is_sealed(self._stored()))
            self.assertEqual(self.ICP.get_param("database.secret"), "legacy-secret")

    def test_without_a_protecting_key_the_secret_stays_readable_in_clear(self):
        for environ in ({sealing.ENV_KEY: sealing.TEST_RUN_KEY}, {sealing.ENV_KEY: ""}):
            with self.subTest(key=bool(environ[sealing.ENV_KEY])):
                with (
                    patch.dict(os.environ, environ),
                    mute_logger("odoo.addons.base.models.ir_config_parameter"),
                ):
                    self.ICP.set_param("database.secret", "clear-secret")
                    self.ICP._seal_sealed_parameters()

                    self.assertEqual(self._stored(), "clear-secret")
                    self.assertEqual(
                        self.ICP.get_param("database.secret"), "clear-secret"
                    )

    def test_sealing_changes_no_signature_and_no_session_token(self):
        self._store_in_clear("signing-secret")
        user = self.env.ref("base.user_admin")
        digest = hmac(self.env, "scope", "message")
        session_values = user._get_session_token_values()

        with patch.dict(os.environ, self.real_key):
            self.ICP._seal_sealed_parameters()
            self.assertTrue(sealing.is_sealed(self._stored()))

            self.assertEqual(hmac(self.env, "scope", "message"), digest)
            self.assertEqual(user._get_session_token_values(), session_values)


class TestTypedParams(TransactionCase):
    KEY = "base.test_typed_param"

    def _read(self, reader, raw, default):
        ICP = self.env["ir.config_parameter"]
        if raw is not None:
            ICP.set_param(self.KEY, raw)
        return getattr(ICP, reader)(self.KEY, default)

    def test_valid_values_are_parsed(self):
        self.assertEqual(self._read("get_param_int", "42", 7), 42)
        self.assertEqual(self._read("get_param_float", "42.5", 7.0), 42.5)
        self.assertEqual(self._read("get_param_float", "42", 7.0), 42.0)

    def test_missing_or_blank_falls_back_silently(self):
        for reader, default in (("get_param_int", 7), ("get_param_float", 7.5)):
            with self.subTest(reader=reader):
                self.assertEqual(self._read(reader, None, default), default)
                self.assertEqual(self._read(reader, "", default), default)

    @mute_logger("odoo.addons.base.models.ir_config_parameter")
    def test_unusable_value_falls_back_and_warns(self):
        for reader, default in (("get_param_int", 7), ("get_param_float", 7.5)):
            for raw in ("ten", "1,5", "12px"):
                with self.subTest(reader=reader, raw=raw):
                    self.assertEqual(self._read(reader, raw, default), default)

    @mute_logger("odoo.addons.base.models.ir_config_parameter")
    def test_float_string_is_not_an_int(self):
        self.assertEqual(self._read("get_param_int", "4.5", 7), 7)


class TestSetGetParam(TransactionCase):
    def test_set_get_param_lifecycle(self):
        ICP = self.env["ir.config_parameter"]
        key = "base.test_set_get_param"
        self.assertEqual(ICP.get_param(key, default="fallback"), "fallback")
        self.assertEqual(ICP.get_param(key), False)
        self.assertEqual(ICP.set_param(key, "v1"), False)
        self.assertEqual(ICP.get_param(key), "v1")
        self.assertEqual(ICP.set_param(key, "v2"), "v1")
        self.assertEqual(ICP.get_param(key), "v2")
        self.assertEqual(ICP.set_param(key, 42), "v2")
        self.assertEqual(ICP.get_param(key), "42")
        self.assertEqual(ICP.set_param(key, "42"), "42")
        self.assertEqual(ICP.set_param(key, False), "42")
        self.assertEqual(ICP.get_param(key), False)
        self.assertEqual(ICP.set_param(key, False), False)

    @mute_logger("odoo.db.cursor")
    def test_set_param_create_race(self):
        ICP = self.env["ir.config_parameter"]
        key = "base.test_set_param_race"
        ICP.set_param(key, "concurrent")
        cls = self.registry["ir.config_parameter"]
        original_search = cls.search
        missed = []

        def racy_search(model, domain, *args, **kwargs):
            if not missed and domain == [("key", "=", key)]:
                missed.append(True)
                return model.browse()
            return original_search(model, domain, *args, **kwargs)

        with patch.object(cls, "search", racy_search):
            old = ICP.set_param(key, "winner")

        self.assertTrue(missed, "the racy search stub was not exercised")
        self.assertEqual(old, "concurrent")
        self.assertEqual(ICP.get_param(key), "winner")


class TestSetParamConcurrency(BaseCase):
    KEY = "base.test_set_param_cross_tx_race"

    def setUp(self):
        super().setUp()
        self.addCleanup(self._drop_key)
        self._drop_key()

    def _drop_key(self):
        registry = Registry(common.get_db_name())
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.config_parameter"].search([("key", "=", self.KEY)]).unlink()

    @mute_logger("odoo.db.cursor")
    def test_set_param_concurrent_create_is_retryable(self):
        registry = Registry(common.get_db_name())
        with registry.cursor() as cr_a, registry.cursor() as cr_b:
            env_a = odoo.api.Environment(cr_a, common.ADMIN_USER_ID, {})
            env_b = odoo.api.Environment(cr_b, common.ADMIN_USER_ID, {})
            for env in (env_a, env_b):
                env["ir.config_parameter"].search_count([("key", "=", self.KEY)])

            env_a["ir.config_parameter"].set_param(self.KEY, "winner")
            cr_a.commit()

            with self.assertRaises(ConcurrencyError):
                env_b["ir.config_parameter"].set_param(self.KEY, "loser")

            cr_b.rollback()
            env_b = odoo.api.Environment(cr_b, common.ADMIN_USER_ID, {})
            self.assertEqual(
                env_b["ir.config_parameter"].set_param(self.KEY, "loser"), "winner"
            )
