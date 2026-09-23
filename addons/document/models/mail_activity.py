from datetime import datetime

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    request_document_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="request_activity_id",
        string="Requested Documents",
    )
    is_document_request = fields.Boolean(
        compute="_compute_is_document_request",
        store=True,
    )

    @api.depends("request_document_ids")
    def _compute_is_document_request(self) -> None:
        for activity in self:
            activity.is_document_request = bool(activity.request_document_ids)
        if _debug.logic.enabled:
            _debug.logic(
                "request_flag_computed",
                activities=self,
                requests=len(self.filtered("is_document_request")),
            )

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> MailActivity:
        # No document names an activity before it exists: saying so spares the
        # compute a one2many read per batch; the link below sets it when made.
        for vals in vals_list:
            vals.setdefault("is_document_request", False)
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

        planting = upload_activities.filtered(
            lambda act: (
                act.res_model != "document.document" and act.activity_type_id.folder_id
            )
        )
        self._check_upload_request_folders(planting.activity_type_id.folder_id)
        doc_vals = [
            {
                "res_model": activity.res_model,
                "res_id": activity.res_id,
                "owner_id": activity.activity_type_id.default_user_id.id
                or (self.env.user.id if self.env.user.active else False),
                "folder_id": activity.activity_type_id.folder_id.id,
                "tag_ids": [Command.set(activity.activity_type_id.tag_ids.ids)],
                "name": activity.summary or activity.res_name or "upload file request",
                "request_activity_id": activity.id,
            }
            for activity in planting
        ]
        if doc_vals:
            _debug.pipeline("upload_requests_created", count=len(doc_vals))
            self.env["document.document"].sudo().create(doc_vals)
        return activities

    @api.model
    def _check_upload_request_folders(self, folders: models.Model) -> None:
        if self.env.su or not folders:
            return
        refused = folders.with_env(self.env).filtered(
            lambda folder: folder.user_permission != "edit"
        )
        if refused:
            _debug.logic("upload_request_refused", folders=refused)
            raise AccessError(
                _(
                    "This activity type files the requested document in a folder "
                    "you cannot edit."
                )
            )

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
        documents = (
            self.env["document.document"]
            .sudo()
            .search(
                [
                    ("id", "in", act_on_docs.mapped("res_id")),
                    ("requestee_partner_id", "!=", False),
                    ("request_activity_id", "in", act_on_docs.ids),
                ]
            )
        )
        user = self.env.user
        requested_by_user = documents.filtered(
            lambda document: (
                self.env.su
                or user in (document.owner_id, document.request_activity_id.create_uid)
            )
        )
        if skipped := documents - requested_by_user:
            _debug.logic(
                "request_deadline_not_propagated",
                documents=skipped,
                reason="not_requester",
            )
        if not requested_by_user:
            return write_result
        requestee_accesses = (
            self.env["document.access"]
            .sudo()
            .search(
                Domain("expiration_date", "!=", False)
                & Domain.OR(
                    Domain("document_id", "=", document.id)
                    & Domain("partner_id", "=", document.requestee_partner_id.id)
                    for document in requested_by_user
                )
            )
        )
        by_expiration = requestee_accesses.grouped(
            lambda access: datetime.combine(
                access.document_id.request_activity_id.date_deadline,
                datetime.max.time(),
            )
        )
        for new_expiration_date, accesses in by_expiration.items():
            accesses.filtered(
                lambda access, expiration=new_expiration_date: (
                    access.expiration_date != expiration
                )
            ).expiration_date = new_expiration_date
        _debug.pipeline(
            "request_deadline_propagated",
            activities=act_on_docs,
            documents=len(documents),
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
                    "tag_ids": [Command.set(next_activity_type.tag_ids.ids)],
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
        # An activity knows whether a document names it as its request, from
        # its own row: closing any other activity asks the document table
        # nothing.
        requests = self.filtered("is_document_request")
        if not requests:
            return super()._action_done(
                feedback=feedback, attachment_ids=attachment_ids
            )
        documents = self.env["document.document"].search(
            [("request_activity_id", "in", requests.ids)]
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
