# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.binary import Binary


class BinaryController(Binary):
    @http.route(
        "/portal/thread/<string:thread_model>/<int:thread_id>/attachment/<int:attachment_id>",
        methods=["GET"],
        type="http",
        auth="public",
    )
    def portal_thread_attachment(self, thread_model, thread_id, attachment_id, **kwargs):
        thread = request.env[thread_model]._get_thread_with_access(
            thread_id, mode=request.env[thread_model]._mail_post_access, **kwargs
        )
        if not thread:
            raise NotFound()
        domain = [
            ("id", "=", int(attachment_id)),
            ("res_id", "=", int(thread_id)),
            ("res_model", "=", thread_model),
        ]
        # sudo: ir.attachment - searching for an attachment on accessible thread is allowed
        attachment_sudo = request.env["ir.attachment"].sudo().search(domain)
        if not attachment_sudo:
            raise NotFound()
        return request.env["ir.binary"]._get_stream_from(attachment_sudo).get_response()

    @http.route(
        [
            "/portal/thread/<string:thread_model>/<int:thread_id>/image/<int:attachment_id>",
            "/portal/thread/<string:thread_model>/<int:thread_id>/image/<int:attachment_id>/<int:width>x<int:height>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def portal_fetch_image(
        self, thread_model, thread_id, attachment_id, width=0, height=0, **kwargs
    ):
        thread = request.env[thread_model]._get_thread_with_access(
            thread_id, mode=request.env[thread_model]._mail_post_access, **kwargs
        )
        if not thread:
            raise NotFound()
        domain = [
            ("id", "=", int(attachment_id)),
            ("res_id", "=", int(thread_id)),
            ("res_model", "=", thread_model),
        ]
        # sudo: ir.attachment - searching for an attachment on accessible thread is allowed
        attachment_sudo = request.env["ir.attachment"].sudo().search(domain, limit=1)
        if not attachment_sudo:
            raise NotFound()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(attachment_sudo, width=int(width), height=int(height))
            .get_response(as_attachment=kwargs.get("download"))
        )
