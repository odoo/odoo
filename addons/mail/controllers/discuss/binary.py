# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.web.controllers.binary import Binary


class BinaryController(Binary):
    @http.route(
        "/discuss/channel/<int:channel_id>/partner/<int:partner_id>/avatar_128",
        methods=["GET"],
        type="http",
        auth="public",
    )
    @add_guest_to_context
    def discuss_channel_partner_avatar_128(self, channel_id, partner_id, **kwargs):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        partner = request.env["res.partner"].browse(partner_id).exists()
        domain = [("channel_id", "=", channel_id), ("partner_id", "=", partner_id)]
        if channel and partner and request.env["discuss.channel.member"].search(domain):
            # sudo: res.partner - the partner is in the same channel as the current user, so they can see their avatar
            return (
                request.env["ir.binary"]._get_image_stream_from(partner.sudo(), field_name="avatar_128").get_response()
            )
        return self.content_image(model="res.partner", id=partner_id, field="avatar_128")

    @http.route(
        "/discuss/channel/<int:channel_id>/guest/<int:guest_id>/avatar_128", methods=["GET"], type="http", auth="public"
    )
    @add_guest_to_context
    def discuss_channel_guest_avatar_128(self, channel_id, guest_id, **kwargs):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        guest = request.env["mail.guest"].browse(guest_id).exists()
        domain = [("channel_id", "=", channel_id), ("guest_id", "=", guest_id)]
        if channel and guest and request.env["discuss.channel.member"].search(domain):
            # sudo: mail.guest - the guest is in the same channel as the current user, so they can see their avatar
            return request.env["ir.binary"]._get_image_stream_from(guest.sudo(), field_name="avatar_128").get_response()
        return self.content_image(model="mail.guest", id=guest_id, field="avatar_128")

    @http.route(
        "/discuss/channel/<int:channel_id>/attachment/<int:attachment_id>", methods=["GET"], type="http", auth="public"
    )
    @add_guest_to_context
    def discuss_channel_attachment(self, channel_id, attachment_id, download=None, **kwargs):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        domain = [
            ("id", "=", int(attachment_id)),
            ("res_id", "=", int(channel_id)),
            ("res_model", "=", "discuss.channel"),
        ]
        # sudo: ir.attachment - searching for an attachment on a specific channel that the current user can access
        attachment_sudo = request.env["ir.attachment"].sudo().search(domain)
        if not attachment_sudo:
            raise NotFound()
        return request.env["ir.binary"]._get_stream_from(attachment_sudo).get_response(as_attachment=download)

    @http.route("/discuss/channel/<int:channel_id>/avatar_128", methods=["GET"], type="http", auth="public")
    @add_guest_to_context
    def discuss_channel_avatar_128(self, channel_id, **kwargs):
        return self.content_image(model="discuss.channel", id=channel_id, field="avatar_128")

    @http.route(
        [
            "/discuss/channel/<int:channel_id>/image/<int:attachment_id>",
            "/discuss/channel/<int:channel_id>/image/<int:attachment_id>/<int:width>x<int:height>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    @add_guest_to_context
    def fetch_image(self, channel_id, attachment_id, width=0, height=0, **kwargs):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        domain = [
            ("id", "=", attachment_id),
            ("res_id", "=", channel_id),
            ("res_model", "=", "discuss.channel"),
        ]
        # sudo: ir.attachment - searching for an attachment on a specific channel that the current user can access
        attachment_sudo = request.env["ir.attachment"].sudo().search(domain, limit=1)
        if not attachment_sudo:
            raise NotFound()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(attachment_sudo, width=int(width), height=int(height))
            .get_response(as_attachment=kwargs.get("download"))
        )
