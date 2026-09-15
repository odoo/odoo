from odoo import models
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import format_datetime, groupby

from odoo.addons.portal.utils import get_url_with_params

_debug = DebugLog(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    _PORTAL_AVATAR_SIZE = "50x50"

    def _compute_is_current_user_or_guest_author(self):
        super()._compute_is_current_user_or_guest_author()
        portal_data = self.env.context.get("portal_data", {})
        portal_partner = portal_data.get("portal_partner")
        portal_thread = portal_data.get("portal_thread")
        if (
            not portal_partner
            or not portal_thread
            or not isinstance(portal_partner, self.pool["res.partner"])
            or not isinstance(portal_thread, self.pool["mixin.mail.thread"])
        ):
            return
        for message in self:
            if (
                message.author_id == portal_partner
                and message.model == portal_thread._name
                and message.res_id == portal_thread.id
            ):
                message.is_current_user_or_guest_author = True

    def portal_message_format(self, options=None):
        self.check_access("read")
        return self._portal_message_format(
            self._portal_get_default_format_properties_names(options=options),
            options=options,
        )

    def _portal_get_default_format_properties_names(self, options=None):
        return {
            "attachment_ids",
            "author_avatar_url",
            "author_id",
            "author_guest_id",
            "body",
            "date",
            "id",
            "is_internal",
            "is_message_subtype_note",
            "message_type",
            "model",
            "published_date_str",
            "res_id",
            "starred",
            "subtype_id",
        }

    def _portal_format_avatar_url(self, message, options):
        size = self._PORTAL_AVATAR_SIZE
        url = f"/mail/avatar/mail.message/{message.id}/author_avatar/{size}"
        if options and options.get("token"):
            return get_url_with_params(url, {"access_token": options["token"]})
        if options and options.get("hash") and options.get("pid"):
            return get_url_with_params(
                url, {"_hash": options["hash"], "pid": options["pid"]}
            )
        return f"/web/image/mail.message/{message.id}/author_avatar/{size}"

    def _portal_message_format(self, properties_names, options=None):
        properties_names = set(properties_names)

        message_to_attachments = {}
        if "attachment_ids" in properties_names:
            properties_names.remove("attachment_ids")
            attachments_sudo = self.sudo().attachment_ids
            related_attachments = {
                att_read_values["id"]: att_read_values
                for att_read_values in attachments_sudo.read(
                    [
                        "checksum",
                        "has_thumbnail",
                        "id",
                        "mimetype",
                        "name",
                        "res_id",
                        "res_model",
                    ]
                )
            }
            message_to_attachments = {
                message.id: [
                    message._portal_message_format_attachments(
                        related_attachments[att_id]
                    )
                    for att_id in message.attachment_ids.ids
                ]
                for message in self.sudo()
            }

        fnames = {
            property_name
            for property_name in properties_names
            if property_name in self._fields
        }
        vals_list = self._read_format(fnames)

        note_id = (
            self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
            if "is_message_subtype_note" in properties_names
            else None
        )
        for message, values in zip(self, vals_list, strict=True):
            if "body" in values:
                values["body"] = ["markup", values["body"]]
            if message_to_attachments:
                values["attachment_ids"] = message_to_attachments.get(message.id, [])
            if "author_avatar_url" in properties_names:
                values["author_avatar_url"] = self._portal_format_avatar_url(
                    message, options
                )
            if "is_message_subtype_note" in properties_names:
                values["is_message_subtype_note"] = message.subtype_id.id == note_id
            if "published_date_str" in properties_names:
                values["published_date_str"] = (
                    format_datetime(self.env, message.date) if message.date else ""
                )
            reaction_groups = []
            for content, reactions_iter in groupby(
                message.sudo().reaction_ids, lambda r: r.content
            ):
                reaction_records = self.env["mail.message.reaction"].union(
                    *reactions_iter
                )
                reaction_groups.append(
                    {
                        "content": content,
                        "count": len(reaction_records),
                        "guests": [
                            {"id": guest.id, "name": guest.name}
                            for guest in reaction_records.guest_id
                        ],
                        "message": message.id,
                        "partners": [
                            {"id": partner.id, "name": partner.name}
                            for partner in reaction_records.partner_id.sudo()
                        ],
                    },
                )
            values.update(
                {
                    "reactions": reaction_groups,
                    "author_id": {
                        "id": message.author_id.id,
                        "name": message.author_id.name,
                    }
                    if message.author_id
                    else False,
                    "thread": {
                        "has_mail_thread": message._is_thread_model(),
                        "id": message.res_id,
                        "model": message.model,
                    },
                }
            )
        _by_message, readable_links = self._get_linked_messages()
        linked_messages = readable_links - self
        linked_messages_vals_list = linked_messages._read_format(
            {"id", "model", "res_id"}
        )
        record_by_linked_message = linked_messages._record_by_message()
        for message, values in zip(
            linked_messages, linked_messages_vals_list, strict=True
        ):
            record = record_by_linked_message.get(message)
            values["thread"] = {
                "display_name": record.sudo().display_name if record else False
            }
        vals_list.extend(linked_messages_vals_list)
        return vals_list

    def _portal_message_format_attachments(self, attachment_values):
        self.check_singleton()
        # The bulk read is shared across messages; ownership belongs to this message.
        attachment_values = dict(attachment_values)
        safari = (
            request
            and request.httprequest.user_agent
            and request.httprequest.user_agent.browser == "safari"
        )
        attachment_values["filename"] = attachment_values["name"]
        attachment_values["mimetype"] = (
            "application/octet-stream"
            if safari and "video" in (attachment_values["mimetype"] or "")
            else attachment_values["mimetype"]
        )
        attachment = self.env["ir.attachment"].browse(attachment_values["id"])
        attachment_values["raw_access_token"] = attachment._get_raw_access_token()
        attachment_values["thumbnail_access_token"] = attachment._get_thumbnail_token()
        if self.is_current_user_or_guest_author:
            attachment_values["ownership_token"] = attachment._get_ownership_token()
        return attachment_values
