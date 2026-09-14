from odoo.exceptions import UserError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestAttachmentUnlinkProtection(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Approver Attachment Test",
                "login": "approver_attachment",
                "email": "approver_attach@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0042",
                "name": "Test Attachment Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(cls.category, cls.approver_user, required=True)

    def _draft_request_with_attachment(self, name):
        request = self.env["approval.request"].create(
            {
                "name": name,
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test_file.pdf",
                "res_model": "approval.request",
                "res_id": request.id,
                "type": "binary",
                "datas": "dGVzdA==",
            }
        )
        return request, attachment

    def test_attachment_unlink_blocked_on_approved_request(self):
        request, attachment = self._draft_request_with_attachment(
            "Test Attachment Approved",
        )
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        self.assertEqual(request.state, "approved")
        with self.assertRaises(UserError):
            attachment.unlink()

    def test_attachment_unlink_allowed_on_draft_request(self):
        request, attachment = self._draft_request_with_attachment(
            "Test Attachment Draft",
        )
        self.assertEqual(request.state, "new")
        attachment.unlink()
        self.assertFalse(attachment.exists())

    def test_attachment_unlink_blocked_on_cancel_request(self):
        request, attachment = self._draft_request_with_attachment(
            "Test Attachment Cancel",
        )
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_refuse()
        self.assertEqual(request.state, "refused")
        with self.assertRaises(UserError):
            attachment.unlink()

    def test_attachment_create_blocked_in_approved(self):
        request, _ = self._draft_request_with_attachment("Approved Create Block")
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        with self.assertRaises(UserError):
            self.env["ir.attachment"].create(
                {
                    "name": "after_approval.pdf",
                    "res_model": "approval.request",
                    "res_id": request.id,
                    "type": "binary",
                    "datas": "dGVzdA==",
                }
            )

    def test_attachment_create_blocked_in_cancel(self):
        request, _ = self._draft_request_with_attachment("Cancel Create Block")
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_refuse()
        with self.assertRaises(UserError):
            self.env["ir.attachment"].create(
                {
                    "name": "after_cancel.pdf",
                    "res_model": "approval.request",
                    "res_id": request.id,
                    "type": "binary",
                    "datas": "dGVzdA==",
                }
            )

    def test_attachment_write_blocked_in_terminal(self):
        request, attachment = self._draft_request_with_attachment("Write Block")
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        with self.assertRaises(UserError):
            attachment.write({"name": "renamed.pdf"})

    def _terminal_attachment(self, name):
        request, attachment = self._draft_request_with_attachment(name)
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        self.assertEqual(request.state, "approved")
        return attachment

    def test_attachment_storage_bookkeeping_write_allowed_in_terminal(self):
        attachment = self._terminal_attachment("Bookkeeping Write OK")
        attachment.write({"access_token": "storage-bookkeeping-probe"})
        self.assertEqual(attachment.access_token, "storage-bookkeeping-probe")

    def test_attachment_mixed_write_blocked_in_terminal(self):
        attachment = self._terminal_attachment("Mixed Write Block")
        with self.assertRaises(UserError):
            attachment.write({"access_token": "probe", "name": "renamed.pdf"})
        with self.assertRaises(UserError):
            attachment.write({"description": "content changed"})

    def test_attachment_s3_mirror_flags_write_allowed_in_terminal(self):
        if "s3_mirror_pending" not in self.env["ir.attachment"]._fields:
            self.skipTest("cloud_storage_s3 is not installed")
        attachment = self._terminal_attachment("S3 Flags Write OK")
        attachment.write(
            {
                "s3_mirror_pending": False,
                "s3_blob_name": attachment.store_fname,
            }
        )
        self.assertEqual(attachment.s3_blob_name, attachment.store_fname)

    def test_attachment_read_allowed_in_terminal(self):
        request, attachment = self._draft_request_with_attachment("Read OK")
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        self.assertEqual(attachment.name, "test_file.pdf")
        self.assertEqual(attachment.res_id, request.id)

    def test_attachment_create_blocked_despite_forged_res_field(self):
        request = self.env["approval.request"].create(
            {
                "name": "Forged res_field",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        self.assertEqual(request.state, "approved")

        with self.assertRaises(UserError):
            self.env["ir.attachment"].create(
                {
                    "name": "smuggled.pdf",
                    "res_model": "approval.request",
                    "res_id": request.id,
                    "res_field": "not_a_real_field",
                    "type": "binary",
                    "datas": "dGVzdA==",
                },
            )

    def test_attachment_nonstored_related_binary_not_exempt(self):
        request = self.env["approval.request"].create(
            {
                "name": "Real Binary Field",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        request.approver_ids[0].with_context(skip_wizard=True).action_approve()
        self.assertEqual(request.state, "approved")

        with self.assertRaises(UserError):
            self.env["ir.attachment"].create(
                {
                    "name": "category_image.png",
                    "res_model": "approval.request",
                    "res_id": request.id,
                    "res_field": "category_image",
                    "type": "binary",
                    "datas": "dGVzdA==",
                },
            )
