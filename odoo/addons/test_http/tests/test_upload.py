# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from io import StringIO
from unittest.mock import patch
from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestHttpUpload(common.HttpCase):
    def test_upload_file_retry(self):
        from odoo.addons.test_http import controllers  # pylint: disable=C0415

        with patch.object(controllers, "should_fail", True), StringIO("Hello world!") as file:
            res = self.url_open("/test_http/upload_file", files={"ufile": file}, timeout=None)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.text, file.getvalue())
