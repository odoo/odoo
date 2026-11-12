# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentHubModule(TransactionCase):
    """ตรวจว่า extension pg_trgm พร้อม และ module ติดตั้งได้"""

    def test_pg_trgm_extension_installed(self):
        self.env.cr.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
        )
        self.assertTrue(self.env.cr.fetchone(), "ต้องมี extension pg_trgm")
