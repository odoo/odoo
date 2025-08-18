from werkzeug.exceptions import NotFound

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.portal.utils import get_portal_partner


class PortalChatter(ThreadController):

    @http.route('/mail/avatar/mail.message/<int:res_id>/author_avatar/<int:width>x<int:height>', type='http', auth='public')
    def portal_avatar(self, res_id=None, height=50, width=50, access_token=None, _hash=None, pid=None):
        """Get the avatar image in the chatter of the portal"""
        if access_token or (_hash and pid):
            message_su = request.env["mail.message"].browse(int(res_id)).exists().sudo()
            thread = self._get_thread_with_access(
                message_su.model, message_su.res_id,
                token=access_token, hash=_hash, pid=pid and int(pid)
            )
            message_su = message_su if thread else request.env["mail.message"]
        else:
            message_su = request.env.ref('web.image_placeholder').sudo()
        # in case there is no message, it creates a stream with the placeholder image
        stream = request.env['ir.binary']._get_image_stream_from(
            message_su, field_name='author_avatar', width=int(width), height=int(height),
        )
        return stream.get_response()

    @http.route("/portal/chatter_init", type="jsonrpc", auth="public", website=True)
    def portal_chatter_init(self, thread_model, thread_id, **kwargs):
        store = Store()
        request.env["res.users"]._init_store_data(store)
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(request.env.user.partner_id, {"is_user_publisher": True})
        thread = self._get_thread_with_access(thread_model, thread_id, **kwargs)
        if thread:
            has_react_access = self._get_thread_with_access_for_post(thread_model, thread_id, **kwargs)
            can_react = has_react_access
            if request.env.user._is_public():
                if portal_partner := get_portal_partner(
                    thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
                ):
                    store.add(
                        thread,
                        {
                            "portal_partner": Store.One(
                                portal_partner,
                                fields=[
                                    "active",
                                    "avatar_128",
                                    Store.One("main_user_id", "share"),
                                    "name",
                                ],
                            )
                        },
                        as_thread=True,
                    )
                can_react = has_react_access and portal_partner
            store.add(
                thread,
                {
                    "can_react": bool(can_react),
                    "hasReadAccess": thread.sudo(False).has_access("read"),
                },
                as_thread=True,
            )
        return store.get_result()

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
            if not request.env.user._is_internal():
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

    @http.route(['/mail/update_is_internal'], type='jsonrpc', auth="user", website=True)
    def portal_message_update_is_internal(self, message_id, is_internal):
        message = request.env['mail.message'].browse(int(message_id))
        message.write({'is_internal': is_internal})
        return message.is_internal
