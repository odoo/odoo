# Copyright 2018 Onestein
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.mail.tools.discuss import Store


class TestAttachmentPreview(BaseCommon):
    def test_get_extension(self):
        attachment = self.env["ir.attachment"].create(
            {
                "datas": base64.b64encode(b"from this, to that."),
                "name": "doc.txt",
            }
        )
        attachment2 = self.env["ir.attachment"].create(
            {
                "datas": base64.b64encode(b"Png"),
                "name": "image.png",
            }
        )
        attachment3 = self.env["ir.attachment"].create(
            {
                "datas": base64.b64encode(b"Png"),
                "name": "image",
            }
        )
        res = self.env["ir.attachment"].get_attachment_extension(attachment.id)
        self.assertEqual(res, "txt")
        store = Store()
        attachment._to_store(store)
        store_data = store.get_result()
        self.assertIn("extension", store_data["ir.attachment"][0])
        res = self.env["ir.attachment"].get_attachment_extension(
            [attachment.id, attachment2.id]
        )
        self.assertEqual(res[attachment.id], "txt")
        self.assertEqual(res[attachment2.id], "png")

        res2 = self.env["ir.attachment"].get_binary_extension(
            "ir.attachment", attachment.id, "datas"
        )
        self.assertTrue(res2)

        module = (
            self.env["ir.module.module"].search([]).filtered(lambda m: m.icon_image)[0]
        )
        res3 = self.env["ir.attachment"].get_binary_extension(
            "ir.module.module", module.id, "icon_image"
        )
        self.assertTrue(res3)

        res4 = self.env["ir.attachment"].get_binary_extension(
            "ir.attachment", attachment3.id, "datas", "name"
        )
        self.assertTrue(res4)

        res5 = self.env["ir.attachment"].get_binary_extension(
            "ir.attachment", attachment.id, None
        )
        self.assertFalse(res5)

        res6 = self.env["ir.attachment"].get_binary_extension(
            "ir.attachment", attachment3.id, "datas", "dummy"
        )
        self.assertTrue(res6)
