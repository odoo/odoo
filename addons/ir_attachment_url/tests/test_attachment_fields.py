# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# Copyright 2020 Ivan Yelizariev <https://twitter.com/yelizariev>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64
import binascii

import requests

from odoo.tests.common import TransactionCase, tagged

TEST_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Flag_of_Turkmenistan.svg/320px-Flag_of_Turkmenistan.svg.png"


@tagged("at_install", "post_install")
class TestAttachmentFields(TransactionCase):
    def _test_end(self, test_record):
        self.assertEqual(test_record.web_icon_data, TEST_URL)
        test_record.invalidate_cache(fnames=["web_icon_data"])
        self.assertEqual(test_record.web_icon_data, TEST_URL)

        test_record = self.env["ir.ui.menu"].browse(test_record.id)
        test_record.invalidate_cache(fnames=["web_icon_data"])

        r = requests.get(TEST_URL, timeout=5)
        r.raise_for_status()
        self.assertEqual(test_record.web_icon_data, base64.b64encode(r.content))

    def test_write(self):
        test_record = self.env["ir.ui.menu"].create(
            {"name": "Turkmenistan (Test record)"}
        )

        with self.assertRaises(binascii.Error):
            test_record.web_icon_data = TEST_URL

        self.assertEqual(test_record.web_icon_data, False)

        test_record = test_record.with_context(
            ir_attachment_url_fields="ir.ui.menu.web_icon_data"
        )
        test_record.web_icon_data = TEST_URL
        self._test_end(test_record)

    def test_create(self):
        TEST_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Flag_of_Turkmenistan.svg/320px-Flag_of_Turkmenistan.svg.png"

        with self.assertRaises(binascii.Error):
            test_record = self.env["ir.ui.menu"].create(
                {"name": "With invalid web_icon_data", "web_icon_data": TEST_URL}
            )

        test_record = (
            self.env["ir.ui.menu"]
            .with_context(ir_attachment_url_fields="ir.ui.menu.web_icon_data")
            .create({"name": "Turkmenistan (Test Record)", "web_icon_data": TEST_URL})
        )
        self._test_end(test_record)
