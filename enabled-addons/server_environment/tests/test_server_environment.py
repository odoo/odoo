# Copyright 2018 Camptocamp (https://www.camptocamp.com).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import os
from unittest.mock import patch

from odoo.tools.config import config as odoo_config

from .. import server_env
from . import common

NO_DEFAULT = [
    "id",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "display_name",
    "config",
    "__last_update",
]


class TestEnv(common.ServerEnvironmentCase):
    def test_view(self):
        model = self.env["server.config"]
        view = model.get_view()
        self.assertTrue(view)

    def _test_default(self, hidden_pwd=False):
        model = self.env["server.config"]
        rec = model.create({})
        fields = model.fields_get()
        defaults = rec.default_get(list(fields))
        fields_with_default = {fld for fld in fields if fld not in NO_DEFAULT}
        self.assertTrue(fields_with_default)
        self.assertIsInstance(defaults, dict)
        self.assertEqual(fields_with_default, set(defaults))
        # Check secrets
        pass_checked = False
        for default in defaults:
            if "_pass" in default:
                check = self.assertEqual if hidden_pwd else self.assertNotEqual
                check(defaults[default], "**********")
                pass_checked = True
        self.assertTrue(pass_checked)
        return defaults

    @patch.dict(odoo_config.options, {"running_env": "dev"})
    def test_default_dev(self):
        self._test_default()

    @patch.dict(odoo_config.options, {"running_env": "whatever"})
    def test_default_non_dev_env(self):
        server_env._load_running_env()
        self._test_default(hidden_pwd=True)

    @patch.dict(odoo_config.options, {"running_env": None})
    @patch.dict(os.environ, {"RUNNING_ENV": "dev"})
    def test_default_dev_from_environ(self):
        server_env._load_running_env()
        self._test_default()

    @patch.dict(odoo_config.options, {"running_env": None})
    @patch.dict(os.environ, {"ODOO_STAGE": "dev"})
    def test_odoosh_dev_from_environ(self):
        server_env._load_running_env()
        self._test_default()

    @patch.dict(odoo_config.options, {"running_env": "testing"})
    def test_value_retrieval(self):
        with self.set_config_dir("testfiles"):
            parser = server_env._load_config()
            val = parser.get("external_service.ftp", "user")
            self.assertEqual(val, "testing")
            val = parser.get("external_service.ftp", "host")
            self.assertEqual(val, "sftp.example.com")

    @patch.dict(odoo_config.options, {"running_env": "testing"})
    def test_default_hidden_password(self):
        with self.load_config(config_dir="testfiles"):
            model = self.env["server.config"]
            model._add_columns()
            self.env.registry.setup_models(self.env.cr)
        defaults = self._test_default(hidden_pwd=True)

        self.assertIn("odoo_I_admin_passwd", defaults)
        self.assertIn("odoo_I_db_password", defaults)
        self.assertIn("odoo_I_smtp_password", defaults)
        self.assertIn("outgoing_mail_provider_promail_I_smtp_pass", defaults)
