# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo_test_helper import FakeModelLoader

from .test_attachment_zipped_download import TestAttachmentZippedDownloadBase


class TestMixin(TestAttachmentZippedDownloadBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.addClassCleanup(cls.loader.restore_registry)
        cls.loader.backup_registry()

        # Imported Test model must be done after the backup_registry
        from .models.res_partner import ResPartner

        cls.loader.update_registry((ResPartner,))

        cls.partner_1 = cls.env["res.partner"].create({"name": "Test partner 1"})
        cls.partner_2 = cls.env["res.partner"].create({"name": "Test partner 2"})
        cls.partner_3 = cls.env["res.partner"].create({"name": "Test partner 3"})

        cls.partner_1_f1 = cls._create_attachment(
            cls.env.uid,
            "partner_1-f1.txt",
            model="res.partner",
            res_id=cls.partner_1.id,
        )
        cls.partner_1_f2 = cls._create_attachment(
            cls.env.uid,
            "partner_1-f2.txt",
            model="res.partner",
            res_id=cls.partner_1.id,
        )
        cls.partner_2_f1 = cls._create_attachment(
            cls.env.uid,
            "partner_2-f1.txt",
            model="res.partner",
            res_id=cls.partner_2.id,
        )

    def test_action_download_attachments_no_attachment(self):
        action = self.partner_3.action_download_attachments()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")

    def test_action_download_attachments_one_attachment(self):
        action = (self.partner_2 | self.partner_3).action_download_attachments()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "self")
        self.assertEqual(
            action["url"], f"/web/content/{self.partner_2_f1.id}?download=1"
        )

    def test_action_download_attachments_two_attachment_one_record(self):
        action = (self.partner_1).action_download_attachments()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "self")
        self.assertTrue(action["url"].startswith("/web/attachment/download_zip?ids="))
        ids = sorted(map(int, action["url"].split("=")[1].split(",")))
        self.assertEqual(ids, (self.partner_1_f1 | self.partner_1_f2).ids)

    def test_action_download_attachments_three_attachment_n_records(self):
        action = (
            self.partner_1 | self.partner_2 | self.partner_3
        ).action_download_attachments()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "self")
        self.assertTrue(action["url"].startswith("/web/attachment/download_zip?ids="))
        ids = sorted(map(int, action["url"].split("=")[1].split(",")))
        self.assertEqual(
            ids, (self.partner_1_f1 + self.partner_1_f2 + self.partner_2_f1).ids
        )
