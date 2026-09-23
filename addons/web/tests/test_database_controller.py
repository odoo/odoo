from unittest.mock import MagicMock, patch

import odoo
from odoo.tests import TransactionCase, tagged

from odoo.addons.web.controllers.database import Database, _is_loopback

CONTROLLER_LOGGER = "odoo.addons.web.controllers.database"


@tagged("web_unit", "database_manager")
class TestDatabaseMasterPassword(TransactionCase):
    def test_is_loopback(self):
        for addr in ("127.0.0.1", "127.0.0.5", "::1", "::ffff:127.0.0.1"):
            self.assertTrue(_is_loopback(addr), addr)
        for addr in (
            "10.0.0.5",
            "203.0.113.7",
            "::ffff:203.0.113.7",
            "2001:db8::1",
            "2002:7f00:1::",
            "64:ff9b::7f00:1",
            "",
            None,
            "not-an-ip",
            "localhost",
        ):
            self.assertFalse(_is_loopback(addr), addr)

    def _promote_calls(self, *, insecure, remote_addr, master_pwd="new-strong-pw"):
        calls = []
        fake_request = MagicMock()
        fake_request.httprequest.remote_addr = remote_addr
        with (
            patch.object(
                odoo.tools.config, "is_valid_admin_password", return_value=insecure
            ),
            patch("odoo.addons.web.controllers.database.request", fake_request),
            patch(
                "odoo.addons.web.controllers.database.dispatch_rpc",
                side_effect=lambda *a, **k: calls.append(a),
            ),
        ):
            Database._handle_insecure_password(object(), master_pwd)
        return calls

    def test_promotes_from_loopback_when_insecure(self):
        with self.assertLogs(CONTROLLER_LOGGER, "WARNING") as capture:
            calls = self._promote_calls(insecure=True, remote_addr="127.0.0.1")
        self.assertEqual(
            calls, [("db", "change_admin_password", ["admin", "new-strong-pw"])]
        )
        self.assertIn("Auto-promoting", capture.output[0])

    def test_promotes_from_ipv6_loopback(self):
        with self.assertLogs(CONTROLLER_LOGGER, "WARNING") as capture:
            calls = self._promote_calls(insecure=True, remote_addr="::1")
        self.assertEqual(len(calls), 1)
        self.assertIn("Auto-promoting", capture.output[0])

    def test_refuses_promotion_from_remote_address(self):
        with self.assertLogs(CONTROLLER_LOGGER, "WARNING") as capture:
            calls = self._promote_calls(insecure=True, remote_addr="203.0.113.7")
        self.assertEqual(calls, [])
        self.assertIn("Refusing to auto-promote", capture.output[0])

    def test_refuses_promotion_when_remote_addr_unknown(self):
        with self.assertLogs(CONTROLLER_LOGGER, "WARNING") as capture:
            calls = self._promote_calls(insecure=True, remote_addr=None)
        self.assertEqual(calls, [])
        self.assertIn("Refusing to auto-promote", capture.output[0])

    def test_noop_when_password_already_secure(self):
        with self.assertNoLogs(CONTROLLER_LOGGER, "WARNING"):
            calls = self._promote_calls(insecure=False, remote_addr="127.0.0.1")
        self.assertEqual(calls, [])

    def test_noop_when_no_master_pwd_submitted(self):
        with self.assertNoLogs(CONTROLLER_LOGGER, "WARNING"):
            calls = self._promote_calls(
                insecure=True, remote_addr="127.0.0.1", master_pwd=""
            )
        self.assertEqual(calls, [])

    def test_an_unwritable_config_still_lets_the_promotion_hold(self):
        fake_request = MagicMock()
        fake_request.httprequest.remote_addr = "127.0.0.1"
        with (
            patch.object(
                odoo.tools.config, "is_valid_admin_password", return_value=True
            ),
            patch.object(odoo.tools.config, "set_admin_password") as set_password,
            patch("odoo.addons.web.controllers.database.request", fake_request),
            patch(
                "odoo.addons.web.controllers.database.dispatch_rpc",
                side_effect=PermissionError("read-only conf"),
            ),
            self.assertLogs(CONTROLLER_LOGGER, "WARNING") as capture,
        ):
            Database._handle_insecure_password(object(), "new-strong-pw")
        set_password.assert_called_once_with("new-strong-pw")
        self.assertIn("could not be written", capture.output[-1])
