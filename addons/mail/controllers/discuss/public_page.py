# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from psycopg2 import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION
from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.misc import get_lang


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
    def discuss_channel_meet_from_token(self, create_token, channel_name=None):
        return self._response_discuss_channel_from_token(
            create_token=create_token, channel_name=channel_name, default_display_mode="video_full_screen"
        )

    @http.route("/chat/<int:channel_id>/<string:invitation_token>", methods=["GET"], type="http", auth="public")
    def discuss_channel_invitation(self, channel_id, invitation_token):
        channel_sudo = request.env["discuss.channel"].browse(channel_id).sudo().exists()
        if not channel_sudo or not channel_sudo.uuid or not consteq(channel_sudo.uuid, invitation_token):
            raise NotFound()
        return self._response_discuss_channel_invitation(channel_sudo=channel_sudo)

    @http.route("/discuss/channel/<int:channel_id>", methods=["GET"], type="http", auth="public")
    def discuss_channel(self, channel_id):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
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
        add_guest_cookie = False
        channel_member_sudo = channel_sudo.env["discuss.channel.member"]._get_as_sudo_from_request(
            request=request, channel_id=channel_sudo.id
        )
        if channel_member_sudo:
            channel_sudo = channel_member_sudo.channel_id  # ensure guest is in context
        else:
            if not channel_sudo.env.user._is_public():
                try:
                    channel_sudo.add_members([channel_sudo.env.user.partner_id.id])
                except UserError:
                    raise NotFound()
            else:
                guest = channel_sudo.env["mail.guest"]._get_guest_from_request(request)
                if guest:
                    channel_sudo = channel_sudo.with_context(guest=guest)
                    try:
                        channel_sudo.add_members(guest_ids=[guest.id])
                    except UserError:
                        raise NotFound()
                else:
                    if channel_sudo.group_public_id:
                        raise NotFound()
                    guest = channel_sudo.env["mail.guest"].create(
                        {
                            "country_id": channel_sudo.env["res.country"]
                            .search([("code", "=", request.geoip.country_code)], limit=1)
                            .id,
                            "lang": get_lang(channel_sudo.env).code,
                            "name": _("Guest"),
                            "timezone": channel_sudo.env["mail.guest"]._get_timezone_from_request(request),
                        }
                    )
                    add_guest_cookie = True
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
        if add_guest_cookie:
            # Discuss Guest ID: every route in this file will make use of it to authenticate
            # the guest through `_get_as_sudo_from_request` or `_get_as_sudo_from_request_or_raise`.
            expiration_date = datetime.now() + timedelta(days=365)
            response.set_cookie(
                guest._cookie_name,
                f"{guest.id}{guest._cookie_separator}{guest.access_token}",
                httponly=True,
                expires=expiration_date,
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
                            "channel": [("insert", {"id": channel_sudo.id, "model": "discuss.channel"})],
                            "shouldDisplayWelcomeViewInitially": channel_sudo.default_display_mode
                            == "video_full_screen",
                        },
                        **discuss_public_view_data,
                    ),
                },
                "session_info": channel_sudo.env["ir.http"].session_info(),
            },
        )
