from datetime import datetime

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> MailActivity:
        activities = super().create(vals_list)
        upload_activities = activities.filtered(
            lambda act: act.activity_category == "upload_file"
        )

        upload_documents_activities = upload_activities.filtered(
            lambda act: act.res_model == "document.document"
        )
        if upload_documents_activities:
            documents = self.env["document.document"].browse(
                upload_documents_activities.mapped("res_id")
            )
            for document, activity in zip(
                documents, upload_documents_activities, strict=True
            ):
                if not document.request_activity_id:
                    _debug.lifecycle(
                        "request_activity_linked", document=document, activity=activity
                    )
                    document.request_activity_id = activity.id

        doc_vals = [
            {
                "res_model": activity.res_model,
                "res_id": activity.res_id,
                "owner_id": activity.activity_type_id.default_user_id.id
                or (self.env.user.id if self.env.user.active else False),
                "folder_id": activity.activity_type_id.folder_id.id,
                "tag_ids": [(6, 0, activity.activity_type_id.tag_ids.ids)],
                "name": activity.summary or activity.res_name or "upload file request",
                "request_activity_id": activity.id,
            }
            for activity in upload_activities.filtered(
                lambda act: (
                    act.res_model != "document.document"
                    and act.activity_type_id.folder_id
                )
            )
        ]
        if doc_vals:
            _debug.pipeline("upload_requests_created", count=len(doc_vals))
            self.env["document.document"].sudo().create(doc_vals)
        return activities

    def write(self, vals: dict) -> bool:
        deadline_changed = "date_deadline" in vals and any(
            activity.date_deadline != fields.Date.to_date(vals["date_deadline"])
            for activity in self
        )
        write_result = super().write(vals)
        if not deadline_changed or not (
            act_on_docs := self.filtered(
                lambda activity: activity.res_model == "document.document"
            )
        ):
            return write_result
        document_requestee_partner_ids = (
            self.env["document.document"]
            .sudo()
            .search_read(
                [
                    ("id", "in", act_on_docs.mapped("res_id")),
                    ("requestee_partner_id", "!=", False),
                    ("request_activity_id", "in", self.ids),
                ],
                ["requestee_partner_id"],
            )
        )
        new_expiration_date = datetime.combine(
            self[0].date_deadline, datetime.max.time()
        )
        self.env["document.access"].sudo().search(
            Domain.OR(
                [
                    ("document_id", "=", document_requestee_partner_id["id"]),
                    (
                        "partner_id",
                        "=",
                        document_requestee_partner_id["requestee_partner_id"][0],
                    ),
                    ("expiration_date", "!=", False),
                    ("expiration_date", "!=", new_expiration_date),
                ]
                for document_requestee_partner_id in document_requestee_partner_ids
            )
        ).expiration_date = new_expiration_date
        _debug.pipeline(
            "request_deadline_propagated",
            activities=act_on_docs,
            documents=len(document_requestee_partner_ids),
        )
        return write_result

    def _prepare_next_activity_values(self) -> dict:
        vals = super()._prepare_next_activity_values()
        current_activity_type = self.activity_type_id
        next_activity_type = current_activity_type.triggered_next_type_id

        if (
            current_activity_type.category == "upload_file"
            and self.res_model == "document.document"
            and next_activity_type.category == "upload_file"
        ):
            existing_document = self.env["document.document"].search(
                [("request_activity_id", "=", self.id)], limit=1
            )
            if "summary" not in vals:
                vals["summary"] = self.summary or _("Upload file request")
            new_doc_request = self.env["document.document"].create(
                {
                    "owner_id": existing_document.owner_id.id,
                    "folder_id": next_activity_type.folder_id.id
                    if next_activity_type.folder_id
                    else existing_document.folder_id.id,
                    "tag_ids": [(6, 0, next_activity_type.tag_ids.ids)],
                    "name": vals["summary"],
                }
            )
            _debug.lifecycle(
                "next_upload_request_created",
                activity=self,
                document=new_doc_request,
            )
            vals["res_id"] = new_doc_request.id
        return vals

    def _action_done(
        self, feedback: str | bool = False, attachment_ids: list[int] | None = None
    ) -> tuple:
        if not self:
            return super()._action_done(
                feedback=feedback, attachment_ids=attachment_ids
            )
        documents = self.env["document.document"].search(
            [("request_activity_id", "in", self.ids)]
        )
        document_without_attachment = documents.filtered(lambda d: not d.attachment_id)
        if document_without_attachment and not feedback:
            feedback = _(
                "Document Request: %(name)s Uploaded by: %(user)s",
                name=document_without_attachment[0].name,
                user=self.env.user.name,
            )
        messages, next_activities = super(
            MailActivity, self.with_context(no_document=True)
        )._action_done(feedback=feedback, attachment_ids=attachment_ids)
        _debug.pipeline(
            "upload_requests_done",
            activities=self,
            documents=documents,
            unfulfilled=len(document_without_attachment),
        )
        documents.filtered(
            lambda document: document.access_via_link == "edit"
        ).access_via_link = "view"
        documents.requestee_partner_id = False
        documents.request_activity_id = False
        if attachment_ids and document_without_attachment:
            document_without_attachment[:1].attachment_id = attachment_ids[0]
        return messages, next_activities
