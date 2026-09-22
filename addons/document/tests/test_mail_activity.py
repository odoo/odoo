from datetime import datetime

from odoo import fields
from odoo.tests.common import tagged

from .test_document_common import GIF, TEXT, TransactionCaseDocuments


@tagged("mail_activity")
class TestDocumentsMailActivity(TransactionCaseDocuments):
    def test_request_activity(self):
        partner = self.env["res.partner"].create({"name": "Pepper Street"})
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "test_activity_type",
                "category": "upload_file",
                "folder_id": self.folder_a.id,
            }
        )
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "user_id": self.doc_user.id,
                "res_id": partner.id,
                "res_model_id": self.env["ir.model"]
                .search([("model", "=", "res.partner")], limit=1)
                .id,
                "summary": "test_summary",
            }
        )

        activity_2 = self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "user_id": self.doc_user.id,
                "res_id": partner.id,
                "res_model_id": self.env["ir.model"]
                .search([("model", "=", "res.partner")], limit=1)
                .id,
                "summary": "test_summary_2",
            }
        )

        attachment = self.env["ir.attachment"].create(
            {
                "datas": GIF,
                "name": "Test activity 1",
            }
        )

        document_1 = self.env["document.document"].search(
            [("request_activity_id", "=", activity.id)], limit=1
        )
        document_2 = self.env["document.document"].search(
            [("request_activity_id", "=", activity_2.id)], limit=1
        )

        self.assertEqual(
            document_1.name,
            "test_summary",
            "the activity document should have the right name",
        )
        self.assertEqual(
            document_1.folder_id.id,
            self.folder_a.id,
            "the document 1 should have the right folder",
        )
        self.assertEqual(
            document_2.folder_id.id,
            self.folder_a.id,
            "the document 2 should have the right folder",
        )
        activity._action_done(attachment_ids=[attachment.id])
        document_2.write({"datas": TEXT, "name": "new filename"})
        self.assertEqual(
            document_1.attachment_id.id,
            attachment.id,
            "the document should have the newly added attachment",
        )
        self.assertFalse(activity.active, "the activity should be done")
        self.assertFalse(activity_2.active, "the activity_2 should be done")

    def test_recurring_document_request(self):
        self.doc_partner = self.env["res.partner"].create(
            {
                "name": "Luke Skywalker",
            }
        )
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "recurring_upload_activity_type",
                "category": "upload_file",
                "folder_id": self.folder_a.id,
            }
        )
        activity_type.write(
            {"chaining_type": "trigger", "triggered_next_type_id": activity_type.id}
        )
        document = (
            self.env["document.request_wizard"]
            .create(
                {
                    "name": "Wizard Request",
                    "requestee_id": self.doc_partner.id,
                    "activity_type_id": activity_type.id,
                    "folder_id": self.folder_a.id,
                }
            )
            .request_document()
        )
        activity = document.request_activity_id

        self.assertEqual(activity.summary, "Wizard Request")

        document.write(
            {
                "attachment_id": self.env["ir.attachment"]
                .create({"datas": GIF, "name": "testGif.gif"})
                .id
            }
        )

        self.assertFalse(
            activity.active, "the activity should be removed after file upload"
        )
        self.assertEqual(document.type, "binary", "document 1 type should be binary")
        self.assertFalse(
            document.request_activity_id, "document 1 should have no activity remaining"
        )

        activity_2 = self.env["mail.activity"].search(
            [
                ("res_model", "=", "document.document"),
                ("activity_type_id", "=", activity_type.id),
            ]
        )
        document_2 = self.env["document.document"].search(
            [
                ("request_activity_id", "=", activity_2.id),
                ("type", "=", "binary"),
                ("attachment_id", "=", False),
            ]
        )

        self.assertNotEqual(
            document_2.id, document.id, "a new document and activity should exist"
        )
        self.assertEqual(document_2.request_activity_id.summary, "Wizard Request")


@tagged("post_install", "-at_install")
class TestDocumentsRequestActivityReschedule(TransactionCaseDocuments):
    def test_reschedule_request_activity_as_viewer_or_owner(self):
        doc = self.env["document.document"].create(
            {
                "type": "binary",
                "name": "req",
                "datas": GIF,
                "owner_id": self.document_manager.id,
                "access_internal": "none",
            }
        )
        requestee = self.portal_user.partner_id
        upload_type = self.env["mail.activity.type"].search(
            [("category", "=", "upload_file")], limit=1
        )
        self.assertTrue(upload_type)
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": upload_type.id,
                "res_model_id": self.env.ref("document.model_document_document").id,
                "res_id": doc.id,
                "user_id": self.internal_user.id,
                "date_deadline": fields.Date.today(),
            }
        )
        doc.write(
            {"requestee_partner_id": requestee.id, "request_activity_id": activity.id}
        )
        old_exp = fields.Datetime.now()
        access = (
            self.env["document.access"]
            .sudo()
            .create(
                {
                    "document_id": doc.id,
                    "partner_id": requestee.id,
                    "role": "view",
                    "expiration_date": old_exp,
                }
            )
        )
        doc.sudo().action_update_access_rights(
            partners={self.internal_user.partner_id: ("view", False)}
        )
        self.assertEqual(doc.with_user(self.internal_user).user_permission, "view")

        new_date = fields.Date.add(fields.Date.today(), days=7)
        activity.with_user(self.internal_user).write({"date_deadline": new_date})
        self.assertEqual(
            access.expiration_date,
            old_exp,
            "only the requester moves the requestee's expiration",
        )

        owner_date = fields.Date.add(fields.Date.today(), days=9)
        activity.with_user(self.document_manager).write({"date_deadline": owner_date})
        self.assertEqual(
            access.expiration_date,
            datetime.combine(owner_date, datetime.max.time()),
            "the owner's reschedule syncs the requestee's expiration (in sudo)",
        )

    def test_request_fulfilment_is_logged_once(self):
        doc = self.env["document.document"].create(
            {"type": "binary", "name": "req.txt", "folder_id": self.folder_a.id}
        )
        activity = doc.activity_schedule(
            "mail.mail_activity_data_todo", user_id=self.doc_user.id
        )
        doc.request_activity_id = activity
        before = doc.message_ids
        doc.with_user(self.doc_user).write({"raw": b"content"})
        doc.invalidate_recordset()
        new_bodies = (doc.message_ids - before).mapped("body")
        self.assertEqual(
            sum("Uploaded by" in body for body in new_bodies),
            1,
            "the activity feedback already says who uploaded what: %s" % new_bodies,
        )
        self.assertFalse(doc.request_activity_id)
