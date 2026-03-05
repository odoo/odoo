# Copyright 2022-2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestAttachmentZippedDownloadBase(BaseCommon):
    @classmethod
    def _create_attachment(cls, user, name, model=False, res_id=False):
        return (
            cls.env["ir.attachment"]
            .with_user(user)
            .create(
                {
                    "name": name,
                    "datas": base64.b64encode(b"\xff data"),
                    "res_model": model,
                    "res_id": res_id,
                }
            )
        )


class TestAttachmentZippedDownload(HttpCase, TestAttachmentZippedDownloadBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="test-user")
        test_1 = cls._create_attachment(cls.user, "test1.txt")
        test_2 = cls._create_attachment(cls.user, "test2.txt")
        cls.attachments = test_1 + test_2

    def test_action_attachments_download(self):
        self.authenticate("test-user", "test-user")
        res = self.attachments.action_attachments_download()
        response = self.url_open(res["url"], timeout=20)
        self.assertEqual(response.status_code, 200)


class TestAttachmentZipped(TestAttachmentZippedDownloadBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="test-user",
            password="test-user",
            groups="base.group_user,base.group_partner_manager",
        )
        test_1 = cls._create_attachment(cls.user, "test1.txt")
        test_2 = cls._create_attachment(cls.user, "test2.txt")
        test_3 = cls._create_attachment(
            cls.user,
            "test3.txt",
            model="res.partner",
            res_id=cls.user.partner_id.id,
        )
        cls.attachments = test_1 + test_2 + test_3

    def test_create_temp_zip(self):
        res = self.attachments._create_temp_zip()
        self.assertTrue(res)

    def test_create_temp_zip_access_denined(self):
        attachments = self.attachments | self._create_attachment(
            self.uid,
            "test4.txt",
            model="ir.ui.view",
            res_id=self.env.ref("base.view_view_form").id,
        )
        with self.assertRaises(AccessError):
            attachments._create_temp_zip()
