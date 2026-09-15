from urllib.parse import quote

from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq

from odoo.addons.approval_document.models.document_document import (
    DOCUMENT_ACCESS_ROLES,
)
from odoo.addons.document.controllers import document as document_controller
from odoo.addons.document.controllers import home as document_home

_debug = DebugLog(__name__)


def _request_access_url(access_token):
    return f"/documents/request_access/{quote(access_token, safe='')}"


def _requestable_document(access_token):
    document_token, document_id = document_controller.ShareRoute._split_access_token(
        access_token
    )
    if not document_id:
        _debug.logic("not_requestable", reason="malformed_token")
        return request.env["document.document"]
    document_sudo = request.env["document.document"].sudo().browse(document_id).exists()
    if not (
        document_sudo
        and document_sudo.document_token
        and document_token.isascii()
        and consteq(document_token, document_sudo.document_token)
    ):
        _debug.logic("not_requestable", reason="token_mismatch", document=document_id)
        return request.env["document.document"]
    target_sudo = document_sudo.shortcut_document_id or document_sudo
    if not target_sudo.active:
        _debug.logic("not_requestable", reason="archived", document=target_sudo)
        return request.env["document.document"]
    return target_sudo


def _is_requestable(access_token):
    return (
        not request.env.user._is_public()
        and bool(_requestable_document(access_token))
        and not document_controller.ShareRoute._from_access_token(
            access_token, skip_log=True
        )
    )


class ShareRoute(document_controller.ShareRoute):
    @http.route()
    def documents_home(self, access_token, member_id="", member_signup_token=""):
        if _is_requestable(access_token):
            _debug.pipeline("home_redirected_to_request", by="share_route")
            return request.redirect(_request_access_url(access_token))
        return super().documents_home(
            access_token, member_id=member_id, member_signup_token=member_signup_token
        )

    @http.route(
        "/documents/request_access/<access_token>",
        type="http",
        auth="user",
        methods=["GET", "POST"],
    )
    def documents_request_access(self, access_token, role=None, **kwargs):
        document_sudo = _requestable_document(access_token)
        if not document_sudo:
            _debug.logic("access_request_page_refused", reason="not_requestable")
            return request.render(
                "document.not_available", {"document": document_sudo}, status=404
            )
        if document_sudo.with_user(request.env.user).user_permission != "none":
            _debug.logic(
                "access_request_page_skipped",
                reason="already_permitted",
                document=document_sudo,
            )
            return request.redirect(f"/documents/{quote(access_token, safe='')}")
        partner = request.env.user.partner_id
        values = {"access_token": access_token, "requested_role": False, "error": ""}
        if request.httprequest.method == "POST":
            if role not in DOCUMENT_ACCESS_ROLES:
                raise BadRequest
            try:
                document_sudo._request_access(partner, role)
                values["requested_role"] = role
            except UserError as error:
                _debug.logic("access_request_failed", document=document_sudo, role=role)
                values["error"] = error.args[0]
        else:
            values["requested_role"] = next(
                (
                    held
                    for held in DOCUMENT_ACCESS_ROLES
                    if document_sudo._get_live_access_request(partner, held)
                ),
                False,
            )
        return request.render("approval_document.document_request_access", values)


class Home(document_home.Home):
    @route()
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action, **kw)
        access_token = self._share_access_token(kw.get("subpath", ""), request.params)
        if (
            access_token
            and "/" not in access_token
            and request.env.user._is_internal()
            and _is_requestable(access_token)
        ):
            _debug.pipeline("home_redirected_to_request", by="web_client")
            return request.redirect(_request_access_url(access_token))
        return response
