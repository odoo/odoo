from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, JsonRpcException, tagged
from odoo.tools import mute_logger

from .test_document_common import GIF, TransactionCaseDocuments
from odoo.addons.base.models.ir_cron import IrCron
from odoo.addons.mail.tests.common import mail_new_test_user

CHOSEN_TOKEN = "A" * 22


@tagged("post_install", "-at_install")
class TestShareUserAccessSettingsOverHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = mail_new_test_user(
            cls.env,
            login="hardening_owner",
            groups="document.group_documents_user",
            name="Hardening Owner",
        )
        cls.portal = mail_new_test_user(
            cls.env,
            login="hardening_portal",
            groups="base.group_portal",
            name="Hardening Portal",
        )
        cls.colleague = mail_new_test_user(
            cls.env,
            login="hardening_colleague",
            groups="base.group_user",
            name="Hardening Colleague",
        )
        Document = cls.env["document.document"].with_user(cls.owner)
        cls.folder = Document.create({"name": "Hardening Folder", "type": "folder"})
        cls.sub_folder = Document.create(
            {"name": "Portal Sub", "type": "folder", "folder_id": cls.folder.id}
        )
        cls.sub_folder.action_update_access_rights(
            partners={cls.portal.partner_id: ("edit", False)}
        )
        cls.file = Document.create(
            {
                "name": "hello.txt",
                "type": "binary",
                "raw": b"hello",
                "mimetype": "text/plain",
                "folder_id": cls.sub_folder.id,
            }
        )
        cls.env.flush_all()

    def _call(self, record, method, *args, **kwargs):
        return self.call_jsonrpc(
            f"/web/dataset/call_kw/{record._name}/{method}",
            {
                "model": record._name,
                "method": method,
                "args": [record.ids, *args],
                "kwargs": kwargs,
            },
        )

    def _assert_refused(self, record, method, *args, **kwargs):
        with (
            mute_logger("odoo.http"),
            self.assertRaises(JsonRpcException) as caught,
        ):
            self._call(record, method, *args, **kwargs)
        self.assertEqual(str(caught.exception), "odoo.exceptions.AccessError")

    def _anonymous_content_status(self, token):
        self.logout()
        return self.url_open(f"/documents/content/{token}").status_code

    def test_the_portal_editor_is_an_editor(self):
        self.assertEqual(
            self.file.with_user(self.portal).user_permission,
            "edit",
        )
        self.authenticate("hardening_portal", "hardening_portal")
        self._call(self.file, "write", {"name": "renamed.txt"})
        self.file.invalidate_recordset()
        self.assertEqual(self.file.name, "renamed.txt")

    def test_portal_editor_cannot_open_the_file_to_everyone(self):
        self.authenticate("hardening_portal", "hardening_portal")
        self._assert_refused(
            self.file, "write", {"access_internal": "edit", "access_via_link": "edit"}
        )
        self._assert_refused(
            self.sub_folder, "action_update_access_rights", "edit", "edit"
        )
        self._assert_refused(self.file, "write", {"is_download_blocked": True})
        self._assert_refused(
            self.file,
            "action_update_access_rights",
            is_access_via_link_hidden=True,
        )
        self.file.invalidate_recordset()
        self.sub_folder.invalidate_recordset()
        self.assertEqual(
            (self.file.access_internal, self.file.access_via_link), ("none", "none")
        )
        self.assertEqual(
            (self.sub_folder.access_internal, self.sub_folder.access_via_link),
            ("none", "none"),
        )
        self.assertEqual(self._anonymous_content_status(self.file.access_token), 404)

    def test_portal_editor_cannot_grant_members(self):
        self.authenticate("hardening_portal", "hardening_portal")
        self._assert_refused(
            self.sub_folder,
            "action_update_access_rights",
            partners={str(self.colleague.partner_id.id): ["edit", False]},
        )
        self.assertEqual(
            self.sub_folder.with_user(self.colleague).user_permission, "none"
        )

    def test_portal_editor_cannot_choose_the_share_token(self):
        self.file.sudo().access_via_link = "edit"
        self.authenticate("hardening_portal", "hardening_portal")
        self._assert_refused(self.file, "write", {"document_token": CHOSEN_TOKEN})
        self.file.invalidate_recordset()
        self.assertNotEqual(self.file.document_token, CHOSEN_TOKEN)
        self.assertEqual(
            self._anonymous_content_status(f"{CHOSEN_TOKEN}o{self.file.id:x}"), 404
        )

    def test_internal_editor_rotates_the_link_but_cannot_choose_it(self):
        self.file.sudo().access_via_link = "view"
        old_token = self.file.access_token
        self.authenticate("hardening_owner", "hardening_owner")
        self._assert_refused(self.file, "write", {"document_token": CHOSEN_TOKEN})

        self.authenticate("hardening_owner", "hardening_owner")
        self._call(self.file, "action_rotate_document_token")
        self.file.invalidate_recordset()
        new_token = self.file.access_token
        self.assertNotEqual(new_token, old_token)
        self.assertEqual(self._anonymous_content_status(old_token), 404)
        self.assertEqual(self._anonymous_content_status(new_token), 200)

    def test_portal_editor_cannot_rotate_the_link(self):
        old_token = self.file.document_token
        self.authenticate("hardening_portal", "hardening_portal")
        self._assert_refused(self.file, "action_rotate_document_token")
        self.file.invalidate_recordset()
        self.assertEqual(self.file.document_token, old_token)


@tagged("post_install", "-at_install")
class TestDocumentTokenIsServerGenerated(TransactionCaseDocuments):
    def test_create_refuses_a_chosen_token(self):
        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(self.doc_user).create(
                {
                    "name": "chosen.txt",
                    "folder_id": self.folder_a.id,
                    "document_token": CHOSEN_TOKEN,
                }
            )

    def test_server_code_still_sets_a_token(self):
        document = self.env["document.document"].sudo().create({"name": "sudo.txt"})
        document.document_token = CHOSEN_TOKEN
        self.assertEqual(document.document_token, CHOSEN_TOKEN)


@tagged("post_install", "-at_install")
class TestMembershipExpiryBindsTheMember(TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = cls.doc_user
        cls.requestee = cls.doc_user_2
        cls.folder = cls.env["document.document"].create(
            {
                "name": "Requests",
                "type": "folder",
                "owner_id": cls.requester.id,
                "access_internal": "none",
            }
        )
        cls.activity_type = cls.env["mail.activity.type"].create(
            {
                "name": "Hardening request",
                "category": "upload_file",
                "folder_id": cls.folder.id,
            }
        )
        wizard = (
            cls.env["document.request_wizard"]
            .with_user(cls.requester)
            .create(
                {
                    "name": "Signed contract",
                    "requestee_id": cls.requestee.partner_id.id,
                    "activity_type_id": cls.activity_type.id,
                    "folder_id": cls.folder.id,
                    "activity_date_deadline_range_type": "day",
                    "activity_date_deadline_range": 3,
                }
            )
        )
        cls.document = wizard.request_document()
        cls.activity = cls.document.request_activity_id
        cls.access = cls.document.access_ids.filtered(
            lambda access: access.partner_id == cls.requestee.partner_id
        )
        cls.expiration = cls.access.expiration_date

    def test_the_request_binds_the_requestee_with_an_expiry(self):
        self.assertTrue(self.expiration)
        self.assertEqual(self.access.role, "edit")
        self.assertEqual(self.activity.user_id, self.requestee)

    def test_requestee_moving_the_deadline_keeps_the_expiry(self):
        later = fields.Date.today() + relativedelta(years=10)
        self.activity.with_user(self.requestee).date_deadline = later
        self.assertEqual(self.activity.date_deadline, later)
        self.assertEqual(self.access.expiration_date, self.expiration)

    def test_requester_moving_the_deadline_moves_the_expiry(self):
        later = fields.Date.today() + relativedelta(days=10)
        self.activity.with_user(self.requester).date_deadline = later
        self.assertEqual(
            self.access.expiration_date, datetime.combine(later, datetime.max.time())
        )

    def test_requestee_cannot_clear_their_own_expiry(self):
        document = self.document.with_user(self.requestee)
        with self.assertRaises(AccessError):
            document.action_update_access_rights(
                partners={self.requestee.partner_id: ("edit", False)}
            )
        with self.assertRaises(AccessError):
            self.access.with_user(self.requestee).expiration_date = False
        with self.assertRaises(AccessError):
            self.access.with_user(self.requestee).write({"role": "edit"})
        self.assertEqual(self.access.expiration_date, self.expiration)

    def test_requestee_may_leave_and_owner_may_clear_the_expiry(self):
        self.document.with_user(self.requester).action_update_access_rights(
            partners={self.requestee.partner_id: ("edit", False)}
        )
        self.assertFalse(self.access.expiration_date)
        self.document.with_user(self.requestee).action_update_access_rights(
            partners={self.requestee.partner_id: (False, False)}
        )
        self.assertFalse(self.access.exists())

    def test_share_user_cannot_write_membership_rows(self):
        self.document.action_update_access_rights(
            partners={self.portal_user.partner_id: ("edit", False)}
        )
        portal_access = self.document.access_ids.filtered(
            lambda access: access.partner_id == self.portal_user.partner_id
        )
        with self.assertRaises(AccessError):
            portal_access.with_user(self.portal_user).expiration_date = False


@tagged("post_install", "-at_install")
class TestDownloadBlockReachesTheChatter(TransactionCaseDocuments):
    def _run_cron(self):
        with patch.object(
            IrCron, "_commit_progress", lambda self, *args, **kwargs: float("inf")
        ):
            self.env["document.access.tracking"]._cron_generate_tracking()

    def _tracked_fields(self, document):
        return set(document.message_ids.tracking_value_ids.field_id.mapped("name"))

    def setUp(self):
        super().setUp()
        self.env["document.access.tracking"].search([]).unlink()
        self.document = self.env["document.document"].create(
            {"name": "blocked.gif", "datas": GIF, "folder_id": self.folder_a.id}
        )

    def test_a_download_block_alone_is_tracked(self):
        self.document.action_update_access_rights(is_download_blocked=True)
        with mute_logger("odoo.addons.document.models.document_access_tracking"):
            self._run_cron()
        self.assertIn("is_download_blocked", self._tracked_fields(self.document))

    def test_a_download_block_beside_an_access_change_is_tracked(self):
        self.document.action_update_access_rights(
            access_internal="edit", is_download_blocked=True
        )
        with mute_logger("odoo.addons.document.models.document_access_tracking"):
            self._run_cron()
        self.assertLessEqual(
            {"is_download_blocked", "access_internal"},
            self._tracked_fields(self.document),
        )


@tagged("post_install", "-at_install")
class TestUploadRequestNeedsTheFolder(TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_folder = cls.env["document.document"].create(
            {
                "name": "HR private",
                "type": "folder",
                "owner_id": False,
                "access_internal": "none",
            }
        )
        cls.upload_type = cls.env["mail.activity.type"].create(
            {
                "name": "Upload to HR private",
                "category": "upload_file",
                "folder_id": cls.private_folder.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Requested From"})

    def _schedule(self, user):
        return (
            self.env["mail.activity"]
            .with_user(user)
            .create(
                {
                    "activity_type_id": self.upload_type.id,
                    "res_model_id": self.env.ref("base.model_res_partner").id,
                    "res_id": self.partner.id,
                    "summary": "planted",
                    "user_id": user.id,
                }
            )
        )

    def _planted(self):
        return (
            self.env["document.document"]
            .sudo()
            .search(
                [("folder_id", "=", self.private_folder.id), ("name", "=", "planted")]
            )
        )

    def test_a_user_who_cannot_edit_the_folder_plants_nothing(self):
        self.assertEqual(
            self.private_folder.with_user(self.doc_user).user_permission, "none"
        )
        with self.assertRaises(AccessError):
            self._schedule(self.doc_user)
        self.assertFalse(self._planted())

    def test_a_folder_editor_still_gets_the_request_document(self):
        self.private_folder.action_update_access_rights(
            partners={self.doc_user.partner_id: ("edit", False)}
        )
        activity = self._schedule(self.doc_user)
        planted = self._planted()
        self.assertEqual(len(planted), 1)
        self.assertEqual(planted.request_activity_id, activity)
        self.assertEqual(
            (planted.res_model, planted.res_id), ("res.partner", self.partner.id)
        )
