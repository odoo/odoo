import os
import unittest
from dataclasses import fields
from unittest.mock import patch

from odoo.db import settings as pool_settings
from odoo.db.settings import PoolSettings
from odoo.libs.settings import SettingsSlot
from odoo.tools.config import configmanager


def _pristine_configmanager():
    scrubbed = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    with patch.dict(os.environ, scrubbed, clear=True):
        return configmanager()


class TestTheDefaultsAreTheOptionDefaults(unittest.TestCase):
    def test_a_bare_instance_equals_a_snapshot_of_an_unparsed_config(self):
        self.assertEqual(
            PoolSettings.from_config(_pristine_configmanager()), PoolSettings()
        )

    def test_every_field_has_a_default(self):
        missing = [
            f.name for f in fields(PoolSettings) if f.default is f.default_factory
        ]
        self.assertEqual(missing, [])


class TestFromConfig(unittest.TestCase):
    def _snapshot(self, **options):
        config = _pristine_configmanager()
        for key, value in options.items():
            config[key] = value
        return PoolSettings.from_config(config)

    def test_falsy_options_become_none_not_empty_strings(self):
        settings = self._snapshot(db_host="", db_port=None, db_password="")
        self.assertIsNone(settings.host)
        self.assertIsNone(settings.port)
        self.assertIsNone(settings.password)

    def test_the_replica_policy_options_are_floats(self):
        settings = self._snapshot(db_replica_max_lag=3.5, db_replica_write_pin="1.5")
        self.assertEqual(
            (settings.replica_max_lag, settings.replica_write_pin), (3.5, 1.5)
        )

    def test_ports_are_integers(self):
        settings = self._snapshot(db_port="5433", db_replica_port=5434)
        self.assertEqual((settings.port, settings.replica_port), (5433, 5434))

    def test_db_name_is_a_tuple(self):
        self.assertEqual(self._snapshot(db_name="a,b").db_names, ("a", "b"))
        self.assertEqual(self._snapshot(db_name=[]).db_names, ())

    def test_gevent_takes_its_own_ceiling_only_when_evented(self):
        config = _pristine_configmanager()
        config["db_maxconn"] = 64
        config["db_maxconn_gevent"] = 8
        self.assertEqual(PoolSettings.from_config(config).maxconn, 64)
        self.assertEqual(PoolSettings.from_config(config, evented=True).maxconn, 8)
        config["db_maxconn_gevent"] = None
        self.assertEqual(PoolSettings.from_config(config, evented=True).maxconn, 64)

    def test_readonly_cursors_follow_the_three_switches(self):
        self.assertFalse(self._snapshot().readonly_cursors)
        self.assertTrue(
            self._snapshot(db_replica_host="replica.example").readonly_cursors
        )
        self.assertTrue(self._snapshot(test_enable=True).readonly_cursors)
        self.assertTrue(self._snapshot(dev_mode=["replica"]).readonly_cursors)


class TestConnectionKeywords(unittest.TestCase):
    def test_the_primary_keywords_omit_what_is_unset(self):
        settings = PoolSettings(host="pg.example", port=5432, user="odoo", sslmode=None)
        self.assertEqual(
            settings.connection_keywords(),
            {"host": "pg.example", "port": 5432, "user": "odoo"},
        )

    def test_the_replica_inherits_each_keyword_it_leaves_unset(self):
        settings = PoolSettings(
            host="pg.example",
            port=5432,
            user="odoo",
            password="pw",
            sslmode="require",
            replica_host="replica.example",
            replica_sslmode="verify-full",
        )
        self.assertEqual(
            settings.connection_keywords(readonly=True),
            {
                "host": "replica.example",
                "port": 5432,
                "user": "odoo",
                "password": "pw",
                "sslmode": "verify-full",
            },
        )

    def test_readonly_false_ignores_the_replica(self):
        settings = PoolSettings(host="pg.example", replica_host="replica.example")
        self.assertEqual(
            settings.connection_keywords(readonly=False)["host"], "pg.example"
        )


class TestTheSlot(unittest.TestCase):
    def test_the_source_is_consulted_on_every_read_until_something_is_installed(self):
        calls: list[int] = []

        def source() -> PoolSettings:
            calls.append(1)
            return PoolSettings()

        slot = SettingsSlot("t", source)
        slot.current()
        slot.current()
        self.assertEqual(len(calls), 2)
        with slot.installed(PoolSettings(template="x")):
            self.assertEqual(slot.current().template, "x")
            self.assertEqual(len(calls), 2)
        self.assertEqual(slot.current().template, "template0")

    def test_override_replaces_fields_on_the_current_snapshot(self):
        slot = SettingsSlot("t", lambda: PoolSettings(host="pg.example"))
        with slot.override(template="tpl_x") as settings:
            self.assertEqual(
                (settings.host, settings.template), ("pg.example", "tpl_x")
            )
            self.assertIs(slot.current(), settings)
        self.assertEqual(slot.current().template, "template0")

    def test_installed_restores_the_previous_value_even_when_nested(self):
        slot = SettingsSlot("t", PoolSettings)
        with slot.installed(PoolSettings(template="outer")):
            with slot.installed(PoolSettings(template="inner")):
                self.assertEqual(slot.current().template, "inner")
            self.assertEqual(slot.current().template, "outer")
        self.assertFalse(slot.is_installed)

    def test_a_slot_with_no_source_refuses_rather_than_guessing(self):
        with self.assertRaisesRegex(RuntimeError, "no settings source"):
            SettingsSlot("t").current()

    def test_the_db_slot_is_fed_by_the_config_module(self):
        import odoo.tools.config  # noqa: F401  installs the provider at import

        self.assertIsInstance(pool_settings.current(), PoolSettings)
        self.assertFalse(pool_settings.slot.is_installed)


if __name__ == "__main__":
    unittest.main()
