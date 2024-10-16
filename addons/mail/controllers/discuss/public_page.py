# Part of Odoo. See LICENSE file for full copyright and licensing details.
import psycopg2.errors
from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq, replace_exceptions
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


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
        store = Store().add_global_values(isChannelTokenSecret=True)
        return self._response_discuss_channel_invitation(store, channel)

    @http.route("/discuss/channel/<int:channel_id>", methods=["GET"], type="http", auth="public")
    @add_guest_to_context
    def discuss_channel(self, channel_id):
        # sudo(): discuss.channel - checking if the channel exists
        channel = request.env["discuss.channel"].sudo().search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        guest_already_known = channel.env["mail.guest"]._get_guest_from_context()
        logged_in = not request.env.user._is_public()
        if not logged_in and not guest_already_known:
            raise NotFound()
        guest_already_member = channel in guest_already_known.sudo().channel_ids
        store = Store()
        if guest_already_known and not guest_already_member:
            store.add_global_values(shouldDisplayWelcomeViewInitially=True)
        return self._response_discuss_public_template(store, channel)

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
            except psycopg2.errors.UniqueViolation:
                # concurrent insert attempt: another request created the channel.
                # commit the current transaction and get the channel.
                request.env.cr.commit()
                channel_sudo = channel_sudo.search([("uuid", "=", create_token)])
        store = Store().add_global_values(isChannelTokenSecret=False)
        return self._response_discuss_channel_invitation(store, channel_sudo.sudo(False))

    def _response_discuss_channel_invitation(self, store, channel):
        # group restriction takes precedence over token
        # sudo - res.groups: can access group public id of parent channel to determine if we
        # can access the channel.
        group_public_id = channel.group_public_id or channel.parent_channel_id.sudo().group_public_id
        if group_public_id and group_public_id not in request.env.user.groups_id:
            raise request.not_found()
        with replace_exceptions(UserError, by=NotFound()):
            # sudo: mail.guest - creating a guest and its member inside a channel of which they have the token
            __, guest = channel.sudo()._find_or_create_persona_for_channel(
                guest_name=_("Guest"),
                country_code=request.geoip.country_code,
                timezone=request.env["mail.guest"]._get_timezone_from_request(request),
                join_channel=False,
            )
        # sudo: mail.guest - checking if the guest is already a member of the channel
        guest_already_member = channel in guest.sudo().channel_ids
        if guest and not guest_already_member:
            store.add_global_values(shouldDisplayWelcomeViewInitially=True)
            channel = channel.with_context(guest=guest)
        return self._response_discuss_public_template(store, channel)

    def _response_discuss_public_template(self, store: Store, channel):
        store.add_global_values(
            companyName=request.env.company.name,
            discuss_public_thread_data={
                "id": channel.id,
                "default_display_mode": channel.default_display_mode,
            },
            inPublicPage=True,
        )
        return request.render(
            "mail.discuss_public_channel_template",
            {
                "data": store.get_result(),
                "session_info": channel.env["ir.http"].session_info(),
            },
        )
