# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class BinaryController(http.Controller):
    @http.route(
        "/discuss/channel/<int:channel_id>/partner/<int:partner_id>/avatar_128",
        methods=["GET"],
        type="http",
        auth="public",
    )
    def discuss_channel_partner_avatar_128(self, channel_id, partner_id):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request(
            request=request, channel_id=channel_id
        )
        partner_sudo = channel_member_sudo.env["res.partner"].browse(partner_id).exists()
        placeholder = partner_sudo._avatar_get_placeholder_path()
        domain = [("channel_id", "=", channel_id), ("partner_id", "=", partner_id)]
        if channel_member_sudo and channel_member_sudo.env["discuss.channel.member"].search(domain, limit=1):
            return (
                request.env["ir.binary"]
                ._get_image_stream_from(partner_sudo, field_name="avatar_128", placeholder=placeholder)
                .get_response()
            )
        if request.env.user.share:
            return request.env["ir.binary"]._get_placeholder_stream(placeholder).get_response()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(partner_sudo.sudo(False), field_name="avatar_128", placeholder=placeholder)
            .get_response()
        )

    @http.route(
        "/discuss/channel/<int:channel_id>/guest/<int:guest_id>/avatar_128", methods=["GET"], type="http", auth="public"
    )
    def discuss_channel_guest_avatar_128(self, channel_id, guest_id):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request(
            request=request, channel_id=channel_id
        )
        guest_sudo = channel_member_sudo.env["mail.guest"].browse(guest_id).exists()
        placeholder = guest_sudo._avatar_get_placeholder_path()
        domain = [("channel_id", "=", channel_id), ("guest_id", "=", guest_id)]
        if channel_member_sudo and channel_member_sudo.env["discuss.channel.member"].search(domain, limit=1):
            return (
                request.env["ir.binary"]
                ._get_image_stream_from(guest_sudo, field_name="avatar_128", placeholder=placeholder)
                .get_response()
            )
        if request.env.user.share:
            return request.env["ir.binary"]._get_placeholder_stream(placeholder).get_response()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(guest_sudo.sudo(False), field_name="avatar_128", placeholder=placeholder)
            .get_response()
        )

    @http.route(
        "/discuss/channel/<int:channel_id>/attachment/<int:attachment_id>", methods=["GET"], type="http", auth="public"
    )
    def discuss_channel_attachment(self, channel_id, attachment_id, download=None):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        domain = [
            ("id", "=", int(attachment_id)),
            ("res_id", "=", int(channel_id)),
            ("res_model", "=", "discuss.channel"),
        ]
        attachment_sudo = channel_member_sudo.env["ir.attachment"].search(domain, limit=1)
        if not attachment_sudo:
            raise NotFound()
        return request.env["ir.binary"]._get_stream_from(attachment_sudo).get_response(as_attachment=download)

    @http.route(
        "/discuss/channel/<int:channel_id>/avatar_128",
        methods=["GET"],
        type="http",
        auth="public",
    )
    def discuss_channel_avatar_128(self, channel_id):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=channel_id
        )
        domain = [("id", "=", channel_id)]
        channel_sudo = channel_member_sudo.env["discuss.channel"].search(domain, limit=1)
        if not channel_sudo:
            raise NotFound()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(channel_sudo, field_name="avatar_128")
            .get_response()
        )

    @http.route(
        [
            "/discuss/channel/<int:channel_id>/image/<int:attachment_id>",
            "/discuss/channel/<int:channel_id>/image/<int:attachment_id>/<int:width>x<int:height>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def fetch_image(self, channel_id, attachment_id, width=0, height=0, **kwargs):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=channel_id
        )
        domain = [
            ("id", "=", attachment_id),
            ("res_id", "=", channel_id),
            ("res_model", "=", "discuss.channel"),
        ]
        attachment_sudo = channel_member_sudo.env["ir.attachment"].search(domain, limit=1)
        if not attachment_sudo:
            raise NotFound()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(attachment_sudo, width=width, height=height)
            .get_response(as_attachment=kwargs.get("download"))
        )
