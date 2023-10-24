# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION
from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq, replace_exceptions
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class PublicPageController(http.Controller):
    @http.route(
        [
            "/chat/<string:create_token>",
            "/chat/<string:create_token>/<string:channel_name>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    @add_guest_to_context
    def discuss_channel_chat_from_token(self, create_token, channel_name=None):
        return self._response_discuss_channel_from_token(create_token=create_token, channel_name=channel_name)

    @http.route(
        [
            "/meet/<string:create_token>",
            "/meet/<string:create_token>/<string:channel_name>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    @add_guest_to_context
    def discuss_channel_meet_from_token(self, create_token, channel_name=None):
        return self._response_discuss_channel_from_token(
            create_token=create_token, channel_name=channel_name, default_display_mode="video_full_screen"
        )

    @http.route("/chat/<int:channel_id>/<string:invitation_token>", methods=["GET"], type="http", auth="public")
    @add_guest_to_context
    def discuss_channel_invitation(self, channel_id, invitation_token):
        channel = request.env["discuss.channel"].browse(channel_id).exists()
        # sudo: discuss.channel - channel access is validated with invitation_token
        if not channel or not channel.sudo().uuid or not consteq(channel.sudo().uuid, invitation_token):
            raise NotFound()
        return self._response_discuss_channel_invitation(channel)

    @http.route("/discuss/channel/<int:channel_id>", methods=["GET"], type="http", auth="public")
    @add_guest_to_context
    def discuss_channel(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_public_template(channel)

    def _response_discuss_channel_from_token(self, create_token, channel_name=None, default_display_mode=False):
        # sudo: ir.config_parameter - reading hard-coded key and using it in a simple condition
        if not request.env["ir.config_parameter"].sudo().get_param("mail.chat_from_token"):
            raise NotFound()
        # sudo: discuss.channel - channel access is validated with invitation_token
        channel_sudo = request.env["discuss.channel"].sudo().search([("uuid", "=", create_token)])
        if not channel_sudo:
            try:
                channel_sudo = channel_sudo.create(
                    {
                        "channel_type": "channel",
                        "default_display_mode": default_display_mode,
                        "group_public_id": None,
                        "name": channel_name or create_token,
                        "uuid": create_token,
                    }
                )
            except IntegrityError as e:
                if e.pgcode != UNIQUE_VIOLATION:
                    raise
                # concurrent insert attempt: another request created the channel.
                # commit the current transaction and get the channel.
                request.env.cr.commit()
                channel_sudo = channel_sudo.search([("uuid", "=", create_token)])
        return self._response_discuss_channel_invitation(channel_sudo.sudo(False), is_channel_token_secret=False)

    def _response_discuss_channel_invitation(self, channel, is_channel_token_secret=True):
        discuss_public_view_data = {
            "isChannelTokenSecret": is_channel_token_secret,
        }
        guest_already_known = channel.env["mail.guest"]._get_guest_from_context()
        with replace_exceptions(UserError, by=NotFound()):
            # sudo: mail.guest - creating a guest and its member inside a channel of which they have the token
            __, guest = channel.sudo()._find_or_create_persona_for_channel(
                guest_name=_("Guest"),
                country_code=request.geoip.country_code,
                timezone=request.env["mail.guest"]._get_timezone_from_request(request),
            )
        if guest and not guest_already_known:
            discuss_public_view_data.update(
                {
                    "shouldDisplayWelcomeViewInitially": True,
                }
            )
            channel = channel.with_context(guest=guest)
        return self._response_discuss_public_template(channel, discuss_public_view_data=discuss_public_view_data)

    def _response_discuss_public_template(self, channel, discuss_public_view_data=None):
        discuss_public_view_data = discuss_public_view_data or {}
        return request.render(
            "mail.discuss_public_channel_template",
            {
                "data": {
                    "channelData": channel._channel_info()[0],
                    "discussPublicViewData": dict(
                        {
                            "shouldDisplayWelcomeViewInitially": channel.default_display_mode == "video_full_screen",
                        },
                        **discuss_public_view_data,
                    ),
                },
                "session_info": channel.env["ir.http"].session_info(),
            },
        )
