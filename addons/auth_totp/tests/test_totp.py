import base64
import hmac
import json
import logging
import os
import re
import struct
import time
from unittest.mock import MagicMock, patch
from xmlrpc.client import Fault

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.tests import HttpCase, get_db_name, new_test_user, tagged
from odoo.tools import mute_logger

from ..controllers.home import Home
from odoo.addons.auth_totp.models.totp import TOTP as auth_TOTP

_logger = logging.getLogger(__name__)


class TestTOTPMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_test = new_test_user(
            cls.env,
            "test_user",
            password="test_user",
            tz="UTC",
        )

        ml = mute_logger("odoo.addons.rpc.controllers.xmlrpc")
        ml.__enter__()
        cls.addClassCleanup(ml.__exit__)

    def install_totphook(self):
        baseline_time = time.time()
        last_offset = 0
        totp_key = None

        def _generate_totp(secret_b32, timestamp):
            """Generate a 6-digit TOTP token using HMAC-SHA1 (RFC 6238)."""
            # The wizard displays the secret space-grouped for readability;
            # normalize exactly like res.users._totp_try_setting does (the
            # passlib TOTP this replaced normalized implicitly).
            key = base64.b32decode(re.sub(r"\s", "", secret_b32).upper())
            counter = int(timestamp / 30)
            mac = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
            offset = mac[-1] & 0xF
            code = struct.unpack_from(">I", mac, offset)[0] & 0x7FFFFFFF
            return str(code % 10**6).zfill(6)

        def totp_hook(self, secret=None, offset=0):
            nonlocal totp_key, last_offset
            last_offset = offset * 30
            if totp_key is None:
                totp_key = secret

            token = _generate_totp(totp_key, baseline_time + last_offset)
            _logger.info("TOTP secret:%s offset:%s token:%s", secret, offset, token)
            return token

        # because not preprocessed by ControllerType metaclass
        totp_hook.routing_type = "json"
        self.env.registry.clear_cache("routing")
        # patch Home to add test endpoint
        Home.totp_hook = http.route("/totphook", type="jsonrpc", auth="none")(totp_hook)

        def totp_match(self, code, t=None, **kwargs):
            # Allow going beyond the 30s window
            return origin_match(self, code, t=baseline_time + last_offset, **kwargs)

        origin_match = auth_TOTP.match
        auth_TOTP.match = totp_match

        # remove endpoint and destroy routing map
        @self.addCleanup
        def _cleanup():
            del Home.totp_hook
            auth_TOTP.match = origin_match
            self.env.registry.clear_cache("routing")


@tagged("post_install", "-at_install")
class TestTOTP(TestTOTPMixin, HttpCase):
    def setUp(self):
        super().setUp()
        self.install_totphook()

    def test_totp(self):
        # 1. Enable 2FA
        self.start_tour("/odoo", "totp_tour_setup", login="test_user")

        # 2. Verify that RPC is blocked because 2FA is on.
        self.assertFalse(
            self.xmlrpc_common.authenticate(
                get_db_name(), "test_user", "test_user", {}
            ),
            "Should not have returned a uid",
        )
        self.assertFalse(
            self.xmlrpc_common.authenticate(
                get_db_name(), "test_user", "test_user", {"interactive": True}
            ),
            "Trying to fake the auth type should not work",
        )
        uid = self.user_test.id
        with self.assertRaisesRegex(Fault, r"Access Denied"), mute_logger("odoo.http"):
            self.xmlrpc_object.execute_kw(
                get_db_name(), uid, "test_user", "res.users", "read", [uid, ["login"]]
            )

        # 3. Check 2FA is required
        with self.assertLogs("odoo.addons.auth_totp.models.res_users", "WARNING") as cm:
            self.start_tour("/", "totp_login_enabled", login=None)

        self.assertEqual(len(cm.output), 1)
        self.assertIn("2FA check: REUSE", cm.output[0])

        # 4. Check 2FA is not requested on saved device and disable it
        self.start_tour("/", "totp_login_device", login=None)

        # 5. Finally, check that 2FA is in fact disabled
        self.start_tour("/", "totp_login_disabled", login=None)

        # 6. Check that rpc is now re-allowed
        uid = self.xmlrpc_common.authenticate(
            get_db_name(), "test_user", "test_user", {}
        )
        self.assertEqual(uid, self.user_test.id)
        [r] = self.xmlrpc_object.execute_kw(
            get_db_name(), uid, "test_user", "res.users", "read", [uid, ["login"]]
        )
        self.assertEqual(r["login"], "test_user")

    def test_totp_administration(self):
        self.start_tour("/web", "totp_tour_setup", login="test_user")
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref(
            "sale.group_sale_order_template", raise_if_not_found=False
        )
        if group_order_template:
            self.env.ref("base.group_user").write(
                {"implied_ids": [(4, group_order_template.id)]}
            )
        self.start_tour("/odoo", "totp_admin_disables", login="admin")
        self.start_tour("/", "totp_login_disabled", login=None)

    @mute_logger("odoo.http")
    def test_totp_authenticate(self):
        """Ensure we don't leak session info from a half-logged-in user."""
        self.start_tour("/odoo", "totp_tour_setup", login="test_user")
        self.url_open("/web/session/logout")

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": {
                "db": get_db_name(),
                "login": "test_user",
                "password": "test_user",
            },
        }
        response = self.url_open(
            "/web/session/authenticate", data=json.dumps(payload), headers=headers
        )
        data = response.json()
        self.assertEqual(data["result"]["uid"], None)

    def test_totp_setup_rate_limited(self):
        """_totp_try_setting (the 2FA setup wizard's code-verification path)
        must be rate-limited exactly like _check_credentials's 'totp' branch:
        without it, the wizard's secret+code pair (a 10**DIGITS code space)
        could be brute-forced through repeated enable() calls."""
        secret = base64.b32encode(os.urandom(20)).decode()
        fake_request = MagicMock()
        fake_request.httprequest.environ = {"REMOTE_ADDR": "203.0.113.1"}
        user = self.user_test.with_user(self.user_test)
        limit = 5  # TOTP_RATE_LIMITS['code_check'][0]
        with patch("odoo.addons.auth_totp.models.res_users.request", fake_request):
            for _ in range(limit):
                # wrong code: rate limit must not trip yet, just a normal reject
                self.assertFalse(user._totp_try_setting(secret, "000000"))
            with self.assertRaises(AccessDenied):
                user._totp_try_setting(secret, "000000")
