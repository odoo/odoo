# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION
from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.http import request
from odoo.tools import consteq
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
        channel_sudo = request.env["discuss.channel"].browse(channel_id).sudo().exists()
        if not channel_sudo or not channel_sudo.uuid or not consteq(channel_sudo.uuid, invitation_token):
            raise NotFound()
        return self._response_discuss_channel_invitation(channel_sudo=channel_sudo)

    @http.route("/discuss/channel/<int:channel_id>", methods=["GET"], type="http", auth="public")
    @add_guest_to_context
    def discuss_channel(self, channel_id):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_context_or_raise(channel_id=int(channel_id))
        return self._response_discuss_public_template(channel_sudo=channel_member_sudo.channel_id)

    def _response_discuss_channel_from_token(self, create_token, channel_name=None, default_display_mode=False):
        if not request.env["ir.config_parameter"].sudo().get_param("mail.chat_from_token"):
            raise NotFound()
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
        return self._response_discuss_channel_invitation(channel_sudo=channel_sudo, is_channel_token_secret=False)

    def _response_discuss_channel_invitation(self, channel_sudo, is_channel_token_secret=True):
        if channel_sudo.channel_type == "chat":
            raise NotFound()
        discuss_public_view_data = {
            "isChannelTokenSecret": is_channel_token_secret,
        }
        guest_already_known = channel_sudo.env["mail.guest"]._get_guest_from_context().exists()
        __, guest = channel_sudo._find_or_create_persona_for_channel(
            guest_name=_("Guest"),
            country_code=request.geoip.country_code,
            timezone=request.env['mail.guest']._get_timezone_from_request(request),
            add_as_member=guest_already_known or not channel_sudo.env.user._is_public(),
        )
        if guest and not guest_already_known:
            discuss_public_view_data.update(
                {
                    "addGuestAsMemberOnJoin": True,
                    "shouldDisplayWelcomeViewInitially": True,
                }
            )
        channel_sudo = channel_sudo.with_context(guest=guest)
        response = self._response_discuss_public_template(
            channel_sudo=channel_sudo, discuss_public_view_data=discuss_public_view_data
        )
        return response

    def _response_discuss_public_template(self, channel_sudo, discuss_public_view_data=None):
        discuss_public_view_data = discuss_public_view_data or {}
        return request.render(
            "mail.discuss_public_channel_template",
            {
                "data": {
                    "channelData": channel_sudo._channel_info()[0],
                    "discussPublicViewData": dict(
                        {
                            "shouldDisplayWelcomeViewInitially": channel_sudo.default_display_mode
                            == "video_full_screen",
                        },
                        **discuss_public_view_data,
                    ),
                },
                "session_info": channel_sudo.env["ir.http"].session_info(),
            },
        )
