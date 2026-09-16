from werkzeug.exceptions import NotFound

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.controllers.utils import to_record_id
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.portal.utils import get_portal_partner

_debug = DebugLog(__name__)


class PortalChatter(ThreadController):
    @http.route(
        "/mail/avatar/mail.message/<int:res_id>/author_avatar/<int:width>x<int:height>",
        type="http",
        auth="public",
    )
    def portal_avatar(
        self, res_id, width, height, access_token=None, _hash=None, pid=None
    ):
        try:
            pid = int(pid) if pid else None
        except ValueError:
            pid = None
        message_su = request.env["mail.message"]
        if access_token or (_hash and pid):
            candidate_su = request.env["mail.message"].browse(res_id).exists().sudo()
            if candidate_su and self._get_thread_with_access(
                candidate_su.model,
                candidate_su.res_id,
                token=access_token,
                hash=_hash,
                pid=pid,
            ):
                message_su = candidate_su
        stream = request.env["ir.binary"]._get_stream_image_from_record(
            message_su,
            field_name="author_avatar",
            width=width,
            height=height,
        )
        return stream.prepare_response()

    @http.route("/portal/chatter_init", type="jsonrpc", auth="public", website=True)
    def portal_chatter_init(self, thread_model, thread_id, **kwargs):
        store = Store()
        request.env["res.users"]._init_store_data(store)
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(request.env.user.partner_id, {"is_user_publisher": True})
        thread = self._get_thread_with_access(thread_model, thread_id, **kwargs)
        if thread:
            has_react_access = self._get_thread_with_access_for_post(
                thread_model, thread_id, **kwargs
            )
            can_react = has_react_access
            if request.env.user._is_public():
                if portal_partner := get_portal_partner(
                    thread,
                    kwargs.get("hash"),
                    kwargs.get("pid"),
                    kwargs.get("token"),
                ):
                    store.add(
                        thread,
                        {
                            "portal_partner": Store.One(
                                portal_partner,
                                fields=[
                                    "active",
                                    "avatar_128",
                                    Store.One("main_user_id", ["partner_id", "share"]),
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
                ["display_name"],
                as_thread=True,
            )
        return store.get_result()

    @http.route("/mail/chatter_fetch", type="jsonrpc", auth="public", website=True)
    def portal_message_fetch(self, thread_model, thread_id, fetch_params=None, **kw):
        if thread_model not in request.env:
            _debug.logic(
                "chatter_fetch_refused", reason="unknown_model", model=str(thread_model)
            )
            raise NotFound
        model = request.env[thread_model]
        field = model._fields.get("website_message_ids")
        if field is None:
            _debug.logic(
                "chatter_fetch_refused",
                reason="not_a_portal_thread",
                model=thread_model,
            )
            raise NotFound
        thread_id = to_record_id(thread_id)
        domain = Domain(
            self._setup_portal_message_fetch_extra_domain(kw)
        ) & model.browse(thread_id)._get_domain_portal_message_fetch(
            message_domain=self._get_domain_non_empty_message()
        )

        Message = request.env["mail.message"]
        if kw.get("token"):
            thread = self._get_thread_with_access(
                thread_model,
                thread_id,
                token=kw.get("token"),
            )
            if not thread:
                _debug.logic(
                    "chatter_fetch_refused",
                    reason="token_rejected",
                    model=thread_model,
                    record=thread_id,
                )
                raise NotFound
            if portal_partner := get_portal_partner(
                thread,
                _hash=None,
                pid=None,
                token=kw.get("token"),
            ):
                request.update_context(
                    portal_data={
                        "portal_partner": portal_partner,
                        "portal_thread": thread,
                    },
                )
            Message = request.env["mail.message"].sudo()
        res = Message._message_fetch(
            domain, **Message._filter_fetch_params(fetch_params)
        )
        messages = res.pop("messages")
        _debug.pipeline(
            "chatter_fetch",
            model=thread_model,
            record=thread_id,
            messages=len(messages),
            by_token=bool(kw.get("token")),
        )
        return {
            **res,
            "data": {"mail.message": messages.portal_message_format(options=kw)},
            "messages": messages.ids,
        }

    def _get_domain_non_empty_message(self):
        return request.env["mixin.mail.thread"]._get_domain_portal_message_non_empty()

    def _setup_portal_message_fetch_extra_domain(self, data) -> Domain:
        return Domain.TRUE

    @http.route(["/mail/update_is_internal"], type="jsonrpc", auth="user", website=True)
    def portal_message_update_is_internal(self, message_id, is_internal):
        message = request.env["mail.message"].browse(to_record_id(message_id))
        _debug.lifecycle(
            "message_is_internal", message=message.id, internal=bool(is_internal)
        )
        message.write({"is_internal": bool(is_internal)})
        return message.is_internal
