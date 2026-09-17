import os
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import SessionExpiredException
from odoo.http.core import _request_stack
from odoo.tests.common import TransactionCase

from odoo.addons.base.models.ir_http import IrHttp as BaseIrHttp


class _FakeSession(dict):
    uid = None


class TestIrHttpAuth(TransactionCase):
    @contextmanager
    def _fake_request(self, env, path="/"):
        # what every consumer of a request may read: an addon's ir.http
        # (website) asks the session and the host for the current website
        fake = SimpleNamespace(
            env=env,
            session=_FakeSession(),
            httprequest=SimpleNamespace(path=path, host="localhost"),
        )
        _request_stack.push(fake)
        try:
            yield fake
        finally:
            _request_stack.pop()

    def test_auth_method_user_rejects_public(self):
        public_uid = self.env.ref("base.public_user").id
        with self._fake_request(self.env(user=public_uid)):
            with self.assertRaises(SessionExpiredException):
                self.registry["ir.http"]._auth_method_user()

    def test_authenticate_explicit_unknown_method(self):
        with self._fake_request(self.env) as fake:
            fake.session = SimpleNamespace(uid=None)
            with self.assertRaises(AccessDenied):
                self.registry["ir.http"]._authenticate_explicit("does_not_exist")

    def test_serve_fallback_skips_non_public(self):
        path = "/non_public_fallback_probe"
        self.env["ir.attachment"].sudo().create(
            {
                "name": "probe.bin",
                "type": "binary",
                "url": path,
                "raw": b"secret",
                "public": False,
            }
        )
        # base's own fallback: an addon's override (website) runs the whole
        # frontend dispatch on top of it, which this fake request cannot carry
        serve_fallback = BaseIrHttp.__dict__["_serve_fallback"].__func__
        with self._fake_request(self.env, path=path):
            self.assertIsNone(
                serve_fallback(self.registry["ir.http"]),
                "non-public binary attachment must not be served by the fallback",
            )

    def test_serve_attachment_public_filter(self):
        path = "/serve_attachment_public_filter_probe"
        Attachment = self.env["ir.attachment"].sudo()
        non_public = Attachment.create(
            {
                "name": "private.bin",
                "type": "binary",
                "url": path,
                "raw": b"secret",
                "public": False,
            }
        )
        public = Attachment.create(
            {
                "name": "public.bin",
                "type": "binary",
                "url": path,
                "raw": b"hello",
                "public": True,
            }
        )
        served = Attachment._get_serve_attachment(
            path, extra_domain=[("public", "=", True)]
        )
        self.assertEqual(
            served,
            public,
            "only the public attachment should match the fallback domain",
        )
        self.assertNotEqual(served, non_public)


class TestIrHttpSessionGc(TransactionCase):
    def test_gc_sessions_vacuums_with_the_configured_inactivity(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sessions.max_inactivity_seconds", "4321"
        )
        with patch.object(http.root.session_store, "vacuum") as vacuum:
            self.env["ir.http"]._gc_sessions()
        vacuum.assert_called_once_with(max_lifetime=4321)

    def test_gc_sessions_is_skipped_by_the_environment_switch(self):
        with (
            patch.dict(os.environ, {"ODOO_SKIP_GC_SESSIONS": "1"}),
            patch.object(http.root.session_store, "vacuum") as vacuum,
        ):
            self.env["ir.http"]._gc_sessions()
        vacuum.assert_not_called()
