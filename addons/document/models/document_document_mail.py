from ast import literal_eval
from typing import Any

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_timedelta

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    @api.constrains("type", "alias_name")
    def _check_alias(self) -> None:
        wrong_records = self.filtered(
            lambda d: (d.type != "folder" or d.shortcut_document_id) and d.alias_name
        )
        if wrong_records:
            _debug.logic(
                "alias_refused", reason="not_a_plain_folder", documents=wrong_records
            )
            raise ValidationError(
                _(
                    "The following documents can't have alias: \n- %(records)s",
                    records="\n-".join(wrong_records.mapped("name")),
                )
            )

    def _log_transition_to_parent_folders(self, body: Any) -> None:
        for folder, children in self.filtered("folder_id").grouped("folder_id").items():
            folder.sudo(self.env.user in children.owner_id).message_post(
                body=body(", ".join(children.mapped("display_name")))
            )

    def _compute_mail_alias_domain_count(self) -> None:
        self.mail_alias_domain_count = (
            self.env["mail.alias.domain"].sudo().search_count([])
        )

    def _notify_get_recipients_groups(
        self,
        message: models.Model,
        model_description: str | None,
        msg_vals: dict | bool = False,
    ) -> list:
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if len(self.ids) != 1:
            return groups

        group_values = {
            "active": True,
            "button_access": {"url": self.access_url},
            "has_button_access": True,
        }
        return [
            (
                "group_documents_document_people_with_access",
                lambda pdata: (
                    (
                        pdata["uid"]
                        and self.with_user(pdata["uid"]).user_permission != "none"
                    )
                    or (
                        pdata["id"]
                        and self.access_via_link != "none"
                        and self.access_ids.filtered(
                            lambda a: a.partner_id.id == pdata["id"] and a.role
                        )
                    )
                ),
                group_values,
            )
        ] + groups

    @api.model
    def message_new(
        self, msg_dict: dict, custom_values: dict | None = None
    ) -> DocumentsDocument:
        custom_values = custom_values or {}

        folder = self.env["document.document"].browse(custom_values.get("folder_id"))

        custom_values["name"] = _("Mail: %s", msg_dict.get("subject"))
        if "company_id" not in custom_values:
            custom_values["company_id"] = folder.company_id.id

        if "tag_ids" not in custom_values:
            custom_values["tag_ids"] = folder.alias_tag_ids.ids

        else:
            tags = custom_values["tag_ids"]
            if tags and isinstance(tags[0], list | tuple):
                if all(len(t) >= 2 and t[0] == Command.LINK for t in tags):
                    tags = [t[1] for t in tags]
                elif len(tags) == 1 and len(tags[0]) == 3 and tags[0][0] == Command.SET:
                    tags = tags[0][2]
                else:
                    tags = []

            custom_values["tag_ids"] = (
                self.env["document.tag"].browse(tags).exists().ids
            )

        custom_values["active"] = False
        _debug.pipeline(
            "mail_gateway_document",
            folder=folder,
            tags=len(custom_values["tag_ids"]),
            attachments=len(msg_dict.get("attachments") or ()),
            active=custom_values["active"],
        )
        return (
            super()
            .message_new(msg_dict, custom_values)
            .with_context(document_message_new=True)
        )

    def _alias_get_creation_values(self) -> dict:
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("document.document").id
        if self.id:
            values["alias_defaults"] = self._prepare_alias_defaults()
            values["alias_defaults"] |= {"folder_id": self.id}
        return values

    def message_post(
        self, *, message_type: str = "notification", **kwargs
    ) -> models.Model:
        return super(
            DocumentsDocument, self.with_context(no_document=True)
        ).message_post(message_type=message_type, **kwargs)

    def _message_post_after_hook(self, message: models.Model, msg_vals: dict) -> Any:
        if message.message_type != "email" or not self.env.context.get(
            "document_message_new"
        ):
            return super()._message_post_after_hook(message, msg_vals)
        _debug.pipeline("mail_to_document_start", document=self)

        m2m_commands = msg_vals["attachment_ids"]
        attachments = self.env["ir.attachment"].browse([x[1] for x in m2m_commands])
        disable_mail_to_document = literal_eval(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("document.disable_mail_to_document", default="0")
        )
        documents = None

        if attachments:
            _debug.logic("mail_to_document", by="attachments", count=len(attachments))
            self.attachment_id = False
            documents = self.env["document.document"].create(
                [
                    {
                        **self._message_post_after_hook_template_values(),
                        "name": attachment.name,
                        "attachment_id": attachment.id,
                        "company_id": self.folder_id.company_id.id,
                    }
                    for attachment in attachments
                ]
            )

            for attachment, document in zip(attachments, documents, strict=True):
                attachment.write(
                    {
                        "res_model": "document.document",
                        "res_id": document.id,
                    }
                )
                sub_message_values = {
                    "author_id": msg_vals.get("author_id"),
                    "body": msg_vals.get("body", ""),
                    "email_from": msg_vals.get("email_from"),
                    "message_type": "email",
                    "subject": msg_vals.get("subject") or self.name,
                    "subtype_id": msg_vals.get("subtype_id"),
                    "subtype_xmlid": msg_vals.get("subtype_xmlid"),
                }
                sub_message_values.pop("model", None)
                sub_message_values.pop("res_id", None)
                sub_message_values.pop("attachment_ids", None)
                document.message_post(**sub_message_values)
        elif not self.attachment_id and not disable_mail_to_document:
            _debug.logic("mail_to_document", by="body")
            attachment = self.env["ir.attachment"].create(
                {
                    "name": msg_vals.get("subject")
                    or msg_vals.get("email_from", _("email")),
                    "type": "binary",
                    "raw": message.body,
                    "mimetype": "application/documents-email",
                    "res_model": "document.document",
                }
            )
            document = self.env["document.document"].create(
                {
                    **self._message_post_after_hook_template_values(),
                    "attachment_id": attachment.id,
                }
            )
            message.res_id = document.id
            attachment.res_id = document.id
            documents = document

        if documents:
            _debug.lifecycle("mail_to_document_created", documents=documents)
            for document in documents:
                if self.create_activity_option:
                    document.documents_set_activity(settings_record=self)
                elif self.folder_id.create_activity_option:
                    document.documents_set_activity(settings_record=self.folder_id)

        return super()._message_post_after_hook(message, msg_vals)

    def _message_post_after_hook_template_values(self) -> dict:
        return {
            "folder_id": self.folder_id.id,
            "owner_id": self.folder_id.owner_id.id,
            "partner_id": self.partner_id.id,
            "tag_ids": self.tag_ids.ids,
        }

    def documents_set_activity(
        self, settings_record: models.Model | None = None
    ) -> None:
        if settings_record and settings_record.create_activity_type_id:
            for record in self:
                activity_vals = {
                    "activity_type_id": settings_record.create_activity_type_id.id,
                    "summary": settings_record.create_activity_summary or "",
                    "note": settings_record.create_activity_note or "",
                }
                if settings_record.create_activity_date_deadline_range > 0:
                    activity_vals["date_deadline"] = fields.Date.context_today(
                        settings_record
                    ) + get_timedelta(
                        settings_record.create_activity_date_deadline_range,
                        settings_record.create_activity_date_deadline_range_type,
                    )
                activity_vals["user_id"] = (
                    settings_record.create_activity_user_id or self.env.user
                ).id
                _debug.lifecycle(
                    "activity_scheduled",
                    document=record,
                    activity_type=settings_record.create_activity_type_id,
                )
                record.activity_schedule(**activity_vals)
