# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.portal.utils import get_portal_partner


class PortalThreadController(ThreadController):
    @http.route("/portal/chatter_init", type="jsonrpc", auth="public", website=True)
    def portal_chatter_init(self, thread_model, thread_id, **kwargs):
        store = Store().add_global_values(request.env.user.sudo(False)._store_init_global_fields)
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(request.env.user.partner_id, {"is_user_publisher": True})
        if thread := self._get_thread_with_access(thread_model, thread_id, **kwargs):
            store.add(
                thread,
                lambda res: self._store_portal_thread_fields(res, **kwargs),
                as_thread=True,
            )
        return store.get_result()

    @classmethod
    def _store_portal_thread_fields(cls, res: Store.FieldList, **kwargs):
        portal_partner_by_thread = {
            thread: get_portal_partner(
                # need to use sudo because portal users might not have the right to read the portal partner
                thread.sudo(), kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token"),
            ) for thread in res.records
        }

        def can_react(thread):
            has_access = cls._get_thread_with_access_for_post(thread._name, thread.id, **kwargs)
            if request.env.user._is_public():
                return bool(has_access and portal_partner_by_thread.get(thread))
            return bool(has_access)

        res.attr("can_react", can_react)
        res.attr("hasReadAccess", lambda t: t.sudo(False).has_access("read"))
        res.one(
            "portal_partner",
            lambda res: (
                res.attr("active"),
                res.one("main_user_id", ["share"]),
                res.attr("name"),
                res.from_method("_store_avatar_fields"),
            ),
            predicate=lambda t: t in portal_partner_by_thread,
            value=portal_partner_by_thread.get,
        )

    @http.route('/mail/chatter_fetch', type='jsonrpc', auth='public', website=True)
    def portal_message_fetch(self, thread_model, thread_id, fetch_params=None, **kw):
        # Only search into website_message_ids, so apply the same domain to perform only one search
        # extract domain from the 'website_message_ids' field
        model = request.env[thread_model]
        field = model._fields['website_message_ids']
        domain = (
            Domain(self._setup_portal_message_fetch_extra_domain(kw))
            & Domain(field.get_comodel_domain(model))
            & Domain("res_id", "=", thread_id)
            & Domain("subtype_id", "=", request.env.ref("mail.mt_comment").id)
            & self._get_non_empty_message_domain()
        )

        # Check access
        Message = request.env['mail.message']
        if kw.get('token'):
            thread = ThreadController._get_thread_with_access(
                thread_model, thread_id, token=kw.get("token"),
            )
            if not thread:  # if token is not correct, raise NotFound
                raise NotFound()
            if portal_partner := get_portal_partner(
                thread, _hash=None, pid=None, token=kw.get("token"),
            ):
                request.update_context(
                    portal_data={"portal_partner": portal_partner, "portal_thread": thread}
                )
            # Non-employee see only messages with not internal subtype (aka, no internal logs)
            domain = Message._get_search_domain_share() & domain
            Message = request.env["mail.message"].sudo()
        res = Message._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        return {
            **res,
            "data": {"mail.message": messages.portal_message_format(options=kw)},
            "messages": messages.ids,
        }

    def _get_non_empty_message_domain(self):
        return Domain(
            "body", "not in", [False, '<span class="o-mail-Message-edited"></span>']
        ) | Domain("attachment_ids", "!=", False)

    def _setup_portal_message_fetch_extra_domain(self, data) -> Domain:
        return Domain.TRUE

    def _prepare_message_data(self, post_data, *, thread, **kwargs):
        post_data = super()._prepare_message_data(post_data, thread=thread, **kwargs)
        if kwargs.get("from_create") and request.env.user._is_public():
            if partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                post_data["author_id"] = partner.id
        return post_data

    @classmethod
    def _can_edit_message(cls, message, hash=None, pid=None, token=None, **kwargs):
        if message.model and message.res_id and message.env.user._is_public():
            thread = request.env[message.model].browse(message.res_id)
            partner = get_portal_partner(thread, _hash=hash, pid=pid, token=token)
            if partner and message.author_id == partner:
                return True
        return super()._can_edit_message(message, hash=hash, pid=pid, token=token, **kwargs)
