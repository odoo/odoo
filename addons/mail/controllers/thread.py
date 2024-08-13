# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools import frozendict
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class ThreadController(http.Controller):

    @http.route("/mail/thread/data/access_rights", methods=["POST"], type="json", auth="user")
    def mail_thread_data_access_rights(self, thread_data):
        """ Returns the access rights of currentuser on the given threads.
        :param thread_data: A dictionary where the key is a model name (string) and the value is a list of integers.
                            Each integer represents the ID of a record with the same model name.
                            Example: {'model_name1': [1, 2, 3], 'model_name2': [4, 5, 6]}
        :type thread_data: dict
        :rtype: Store
        """
        store = Store()
        for thread_model in thread_data:
            threads = request.env[thread_model].with_context(active_test=False).browse(thread_data[thread_model])
            if hasattr(threads, "_get_mail_thread_data_access_rights"):
                threads._get_mail_thread_data_access_rights(store)
            else:
                for thread in threads:
                    store.add(thread, {'hasReadAccess': False, 'hasWriteAccess': False}, as_thread=True)
        return store.get_result()

    @http.route("/mail/thread/data", methods=["POST"], type="json", auth="user")
    def mail_thread_data(self, thread_model, thread_id, request_list):
        thread = request.env[thread_model].with_context(active_test=False).search([("id", "=", thread_id)])
        if not thread:
            return Store(
                request.env[thread_model].browse(thread_id),
                {"hasReadAccess": False, "hasWriteAccess": False},
                as_thread=True,
            ).get_result()
        return Store(thread, as_thread=True, request_list=request_list).get_result()

    @http.route("/mail/thread/messages", methods=["POST"], type="json", auth="user")
    def mail_thread_messages(self, thread_model, thread_id, search_term=None, before=None, after=None, around=None, limit=30):
        domain = [
            ("res_id", "=", int(thread_id)),
            ("model", "=", thread_model),
            ("message_type", "!=", "user_notification"),
        ]
        res = request.env["mail.message"]._message_fetch(domain, search_term=search_term, before=before, after=after, around=around, limit=limit)
        messages = res.pop("messages")
        if not request.env.user._is_public():
            messages.set_message_done()
        return {
            **res,
            "data": Store(messages, for_current_user=True).get_result(),
            "messages": Store.many_ids(messages),
        }

    @http.route("/mail/partner/from_email", methods=["POST"], type="json", auth="user")
    def mail_thread_partner_from_email(self, emails, additional_values=None):
        partners = [
            {"id": partner.id, "name": partner.name, "email": partner.email}
            for partner in request.env["res.partner"]._find_or_create_from_emails(emails, additional_values)
        ]
        return partners

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

    def _prepare_post_data(self, post_data, thread, **kwargs):
        if "body" in post_data:
            post_data["body"] = Markup(post_data["body"])  # contains HTML such as @mentions
        new_partners = []
        if "partner_emails" in kwargs:
            new_partners = [
                record.id
                for record in request.env["res.partner"]._find_or_create_from_emails(
                    kwargs["partner_emails"], kwargs.get("partner_additional_values", {})
                )
            ]
        post_data["partner_ids"] = list(set((post_data.get("partner_ids", [])) + new_partners))
        return post_data

    @http.route("/mail/message/post", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        guest = request.env["mail.guest"]._get_guest_from_context()
        guest.env["ir.attachment"].browse(post_data.get("attachment_ids", []))._check_attachments_access(
            kwargs.get("attachment_tokens")
        )
        if context:
            request.update_context(**context)
        canned_response_ids = tuple(cid for cid in kwargs.get('canned_response_ids', []) if isinstance(cid, int))
        if canned_response_ids:
            # Avoid serialization errors since last used update is not
            # essential and should not block message post.
            request.env.cr.execute("""
                UPDATE mail_canned_response SET last_used=%(last_used)s
                WHERE id IN (
                    SELECT id from mail_canned_response WHERE id IN %(ids)s
                    FOR NO KEY UPDATE SKIP LOCKED
                )
            """, {
                'last_used': datetime.now(),
                'ids': canned_response_ids,
            })
        thread = request.env[thread_model]._get_thread_with_access(
            thread_id, mode=request.env[thread_model]._mail_post_access, **kwargs
        )
        if not thread:
            raise NotFound()
        if thread.env.su:
            thread.env.context = frozendict(
                thread.env.context, mail_create_nosubscribe=True, mail_post_autofollow=False
            )
        post_data = {
                key: value
                for key, value in post_data.items()
                if key in thread._get_allowed_message_post_params()
            }
        message = thread.message_post(
            **self._prepare_post_data(post_data, thread, **kwargs)
        )
        return Store(message, for_current_user=True).get_result()

    @http.route("/mail/message/update_content", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_update_content(self, message_id, body, attachment_ids, attachment_tokens=None, partner_ids=None):
        guest = request.env["mail.guest"]._get_guest_from_context()
        guest.env["ir.attachment"].browse(attachment_ids)._check_attachments_access(attachment_tokens)
        message_sudo = guest.env["mail.message"].browse(message_id).sudo().exists()
        if not message_sudo.is_current_user_or_guest_author and not guest.env.user._is_admin():
            raise NotFound()
        if not message_sudo.model or not message_sudo.res_id:
            raise NotFound()
        body = Markup(body) if body else body  # may contain HTML such as @mentions
        guest.env[message_sudo.model].browse([message_sudo.res_id])._message_update_content(
            message_sudo, body, attachment_ids=attachment_ids, partner_ids=partner_ids
        )
        return Store(message_sudo, for_current_user=True).get_result()
