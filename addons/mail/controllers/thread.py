# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools import frozendict
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


class ThreadController(http.Controller):

    # access helpers
    # ------------------------------------------------------------

    @classmethod
    def _get_message_with_access(cls, message_id, mode="read", **kwargs):
        """ Simplified getter that filters access params only, making model methods
        using strong parameters. """
        message_su = request.env['mail.message'].sudo().browse(message_id).exists()
        if not message_su:
            return message_su
        return request.env['mail.message']._get_with_access(
            message_su.id,
            mode=mode,
            **{
                key: value for key, value in kwargs.items()
                if key in request.env[message_su.model or 'mail.thread']._get_allowed_access_params()
            },
        )

    @classmethod
    def _get_thread_with_access(cls, thread_model, thread_id, mode="read", **kwargs):
        """ Simplified getter that filters access params only, making model methods
        using strong parameters. """
        return request.env[thread_model]._get_thread_with_access(
            int(thread_id), mode=mode, **{
                key: value for key, value in kwargs.items()
                if key in request.env[thread_model]._get_allowed_access_params()
            },
        )

    # main routes
    # ------------------------------------------------------------

    @http.route("/mail/thread/messages", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_messages(self, thread_model, thread_id, fetch_params=None):
        domain = [
            ("res_id", "=", int(thread_id)),
            ("model", "=", thread_model),
            ("message_type", "!=", "user_notification"),
        ]
        res = request.env["mail.message"]._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        if not request.env.user._is_public():
            messages.set_message_done()
        return {
            **res,
            "data": Store(messages).get_result(),
            "messages": messages.ids,
        }

    @http.route("/mail/thread/recipients", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_recipients(self, thread_model, thread_id, message_id=None):
        """ Fetch discussion-based suggested recipients, creating partners on the fly """
        thread = self._get_thread_with_access(thread_model, thread_id, mode='read')
        if message_id:
            message = self._get_message_with_access(message_id, mode="read")
            suggested = thread._message_get_suggested_recipients(
                reply_message=message, no_create=False,
            )
        else:
            suggested = thread._message_get_suggested_recipients(
                reply_discussion=True, no_create=False,
            )
        return [
            {'id': info['partner_id'], 'email': info['email'], 'name': info['name']}
            for info in suggested if info['partner_id']
        ]

    @http.route("/mail/thread/recipients/fields", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_recipients_fields(self, thread_model):
        return {
            'partner_fields': request.env[thread_model]._mail_get_partner_fields(),
            'primary_email_field': [request.env[thread_model]._mail_get_primary_email_field()]
        }

    @http.route("/mail/thread/recipients/get_suggested_recipients", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_recipients_get_suggested_recipients(self, thread_model, thread_id, partner_ids=None, main_email=False):
        """This method returns the suggested recipients with updates coming from the frontend.
        :param thread_model: Model on which we are currently working on.
        :param thread_id: ID of the document we need to compute
        :param partner_ids: IDs of new customers that were edited on the frontend, usually only the customer but could be more.
        :param main_email: New email edited on the frontend linked to the @see _mail_get_primary_email_field
        """
        thread = self._get_thread_with_access(thread_model, thread_id)
        partner_ids = request.env['res.partner'].search([('id', 'in', partner_ids)])
        recipients = thread._message_get_suggested_recipients(reply_discussion=True, additional_partners=partner_ids, primary_email=main_email)
        if partner_ids:
            old_customer_ids = set(thread._mail_get_partners()[thread.id].ids) - set(partner_ids.ids)
            recipients = list(filter(lambda rec: rec.get('partner_id') not in old_customer_ids, recipients))
        return [{key: recipient[key] for key in recipient if key in ['name', 'email', 'partner_id']} for recipient in recipients]

    @http.route("/mail/partner/from_email", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_partner_from_email(self, thread_model, thread_id, emails):
        partners = [
            {"id": partner.id, "name": partner.name, "email": partner.email}
            for partner in request.env[thread_model].browse(thread_id)._partner_find_from_emails_single(
                emails, no_create=not request.env.user.has_group("base.group_partner_manager")
            )
        ]
        return partners

    @http.route("/mail/read_subscription_data", methods=["POST"], type="jsonrpc", auth="user")
    def read_subscription_data(self, follower_id):
        """Computes:
        - message_subtype_data: data about document subtypes: which are
            available, which are followed if any"""
        # limited to internal, who can read all followers
        follower = request.env["mail.followers"].browse(follower_id)
        follower.check_access("read")
        record = request.env[follower.res_model].browse(follower.res_id)
        record.check_access("read")
        # find current model subtypes, add them to a dictionary
        subtypes = record._mail_get_message_subtypes()
        store = Store(subtypes, ["name"]).add(follower, ["subtype_ids"])
        return {
            "store_data": store.get_result(),
            "subtype_ids": subtypes.sorted(
                key=lambda s: (
                    s.parent_id.res_model or "",
                    s.res_model or "",
                    s.internal,
                    s.sequence,
                ),
            ).ids,
        }

    def _prepare_post_data(self, post_data, thread, partner_emails=None, **kwargs):
        partners = request.env["res.partner"].browse(post_data.pop("partner_ids", []))
        if "body" in post_data:
            post_data["body"] = Markup(post_data["body"])  # contains HTML such as @mentions
        if partner_emails:
            partners |= thread._partner_find_from_emails_single(
                partner_emails,
                no_create=not request.env.user.has_group("base.group_partner_manager"),
            )
        if role_ids := post_data.pop("role_ids", []):
            # sudo - res.users: getting partners linked to the role is allowed.
            partners |= request.env["res.users"].sudo().search([("role_ids", "in", role_ids)]).partner_id
        post_data["partner_ids"] = self._filter_message_post_partners(thread, partners).ids
        return post_data

    def _filter_message_post_partners(self, thread, partners):
        if self.env.user._is_internal():
            return partners
        domain = [
            ("res_model", "=", thread._name),
            ("res_id", "=", thread.id),
            ("partner_id", "in", partners.ids),
        ]
        # sudo: mail.followers - filtering partners that are followers is acceptable
        return request.env["mail.followers"].sudo().search(domain).partner_id

    @http.route("/mail/message/post", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        guest = request.env["mail.guest"]._get_guest_from_context()
        guest.env["ir.attachment"].browse(post_data.get("attachment_ids", []))._check_attachments_access(
            kwargs.get("attachment_tokens")
        )
        store = Store()
        request.update_context(message_post_store=store)
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
        # TDE todo: should rely on '_get_mail_message_access'
        thread = self._get_thread_with_access(thread_model, thread_id, mode=request.env[thread_model]._mail_post_access, **kwargs)
        if not thread:
            raise NotFound()
        if not self._get_thread_with_access(thread_model, thread_id, mode="write"):
            thread = thread.with_context(mail_post_autofollow_author_skip=True, mail_post_autofollow=False)
        post_data = {
                key: value
                for key, value in post_data.items()
                if key in thread._get_allowed_message_post_params()
            }
        # sudo: mail.thread - users can post on accessible threads
        message = thread.sudo().message_post(**self._prepare_post_data(post_data, thread, **kwargs))
        return store.add(message).get_result()

    @http.route("/mail/message/update_content", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_message_update_content(self, message_id, body, attachment_ids, attachment_tokens=None, partner_ids=None, **kwargs):
        guest = request.env["mail.guest"]._get_guest_from_context()
        guest.env["ir.attachment"].browse(attachment_ids)._check_attachments_access(attachment_tokens)
        message = self._get_message_with_access(message_id, mode="create", **kwargs)
        if not message or not self._can_edit_message(message, **kwargs):
            raise NotFound()
        # sudo: mail.message - access is checked in _get_with_access and _can_edit_message
        message = message.sudo()
        body = Markup(body) if body else body  # may contain HTML such as @mentions
        thread = request.env[message.model].browse(message.res_id)
        update_data = {
            "attachment_ids": attachment_ids,
            "body": body,
            "partner_ids": partner_ids,
            **kwargs,
        }
        thread._message_update_content(
            message,
            **{
                key: value
                for key, value in update_data.items()
                if key in thread._get_allowed_message_update_params()
            }
        )
        return Store(message).get_result()

    # side check for access
    # ------------------------------------------------------------

    @classmethod
    def _can_edit_message(cls, message, **kwargs):
        return message.sudo().is_current_user_or_guest_author or request.env.user._is_admin()

    @classmethod
    def _can_delete_attachment(cls, message, **kwargs):
        return cls._can_edit_message(message, **kwargs)

    @http.route("/mail/thread/unsubscribe", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_unsubscribe(self, res_model, res_id, partner_ids):
        thread = self.env[res_model].browse(res_id)
        thread.message_unsubscribe(partner_ids)
        return Store(
            thread, [], as_thread=True, request_list=["followers", "suggestedRecipients"]
        ).get_result()

    @http.route("/mail/thread/subscribe", methods=["POST"], type="jsonrpc", auth="user")
    def mail_thread_subscribe(self, res_model, res_id, partner_ids):
        thread = self.env[res_model].browse(res_id)
        thread.message_subscribe(partner_ids)
        return Store(
            thread, [], as_thread=True, request_list=["followers", "suggestedRecipients"]
        ).get_result()
