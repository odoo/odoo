# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class ThreadController(http.Controller):
    @http.route("/mail/thread/data", methods=["POST"], type="json", auth="user")
    def mail_thread_data(self, thread_model, thread_id, request_list):
        thread = request.env[thread_model].with_context(active_test=False).search([("id", "=", thread_id)])
        return thread._get_mail_thread_data(request_list)

    @http.route("/mail/thread/messages", methods=["POST"], type="json", auth="user")
    def mail_thread_messages(self, thread_model, thread_id, before=None, after=None, around=None, limit=30):
        domain = [
            ("res_id", "=", int(thread_id)),
            ("model", "=", thread_model),
            ("message_type", "!=", "user_notification"),
        ]
        messages = request.env["mail.message"]._message_fetch(domain, before, after, around, limit)
        if not request.env.user._is_public():
            messages.set_message_done()
        return messages.message_format()

    @http.route("/mail/read_subscription_data", methods=["POST"], type="json", auth="user")
    def read_subscription_data(self, follower_id):
        """Computes:
        - message_subtype_data: data about document subtypes: which are
            available, which are followed if any"""
        request.env["mail.followers"].check_access_rights("read")
        follower = request.env["mail.followers"].sudo().browse(follower_id)
        follower.ensure_one()
        request.env[follower.res_model].check_access_rights("read")
        record = request.env[follower.res_model].browse(follower.res_id)
        record.check_access_rule("read")
        # find current model subtypes, add them to a dictionary
        subtypes = record._mail_get_message_subtypes()
        followed_subtypes_ids = set(follower.subtype_ids.ids)
        subtypes_list = [
            {
                "name": subtype.name,
                "res_model": subtype.res_model,
                "sequence": subtype.sequence,
                "default": subtype.default,
                "internal": subtype.internal,
                "followed": subtype.id in followed_subtypes_ids,
                "parent_model": subtype.parent_id.res_model,
                "id": subtype.id,
            }
            for subtype in subtypes
        ]
        return sorted(
            subtypes_list,
            key=lambda it: (it["parent_model"] or "", it["res_model"] or "", it["internal"], it["sequence"]),
        )

    def _get_allowed_message_post_params(self):
        return {"attachment_ids", "body", "message_type", "partner_ids", "subtype_xmlid", "parent_id"}

    @http.route("/mail/message/post", methods=["POST"], type="json", auth="public")
    def mail_message_post(self, thread_model, thread_id, post_data):
        thread = request.env[thread_model]._get_from_request_or_raise(request, int(thread_id))
        if "body" in post_data:
            post_data["body"] = Markup(post_data["body"])  # contains HTML such as @mentions
        message_data = thread.message_post(
            **{key: value for key, value in post_data.items() if key in self._get_allowed_message_post_params()}
        ).message_format()[0]
        if "temporary_id" in request.context:
            message_data["temporary_id"] = request.context["temporary_id"]
        return message_data

    @http.route("/mail/message/update_content", methods=["POST"], type="json", auth="public")
    def mail_message_update_content(self, message_id, body, attachment_ids):
        guest = request.env["mail.guest"]._get_guest_from_request(request)
        message_sudo = guest.env["mail.message"].browse(message_id).sudo().exists()
        if not message_sudo.is_current_user_or_guest_author and not guest.env.user._is_admin():
            raise NotFound()
        if not message_sudo.model or not message_sudo.res_id:
            raise NotFound()
        request.env[message_sudo.model].browse([message_sudo.res_id])._message_update_content(
            message_sudo, body, attachment_ids=attachment_ids
        )
