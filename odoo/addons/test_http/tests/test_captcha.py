from contextlib import contextmanager
from http import HTTPStatus
from unittest.mock import patch

from odoo import http
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCaptcha(HttpCase):
    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    @contextmanager
    def patch_captcha_valid(self, validity):
        def _verify_request_recaptcha_token(self, captcha):
            if not validity:
                raise UserError("CAPTCHA test")
        with patch.object(self.env.registry['ir.http'], '_verify_request_recaptcha_token', _verify_request_recaptcha_token):
            yield

    def test_post_valid(self):
        with self.patch_captcha_valid(True):
            res = self.url_open('/web/login', data={'csrf_token': http.Request.csrf_token(self), 'login': '_', 'password': '_'})
            res.raise_for_status()

    @mute_logger('odoo.http')
    def test_post_invalid(self):
        with self.patch_captcha_valid(False):
            res = self.url_open('/web/login', data={'csrf_token': http.Request.csrf_token(self), 'login': '_', 'password': '_'})
            self.assertEqual(res.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
            self.assertIn("CAPTCHA test", res.text)

    def test_get_valid(self):
        res = self.url_open('/web/login')
        with self.patch_captcha_valid(True):
            res.raise_for_status()

    def test_get_invalid(self):
        res = self.url_open('/web/login')
        with self.patch_captcha_valid(False):
            res.raise_for_status()
