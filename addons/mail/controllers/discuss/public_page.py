# Part of Odoo. See LICENSE file for full copyright and licensing details.
import psycopg2.errors
from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq, email_normalize, replace_exceptions
from odoo.tools.misc import verify_hash_signed
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


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
    def discuss_channel_invitation(self, channel_id, invitation_token, email_token=None):
        guest_email = email_token and verify_hash_signed(
            self.env(su=True), "mail.invite_email", email_token
        )
        guest_email = email_normalize(guest_email)
        channel = request.env["discuss.channel"].browse(channel_id).exists()
        # sudo: discuss.channel - channel access is validated with invitation_token
        if not channel or not channel.sudo().uuid or not consteq(channel.sudo().uuid, invitation_token):
            raise NotFound()
        store = Store().add_global_values(isChannelTokenSecret=True)
        return self._response_discuss_channel_invitation(store, channel, guest_email)

    @http.route("/discuss/channel/<int:channel_id>", methods=["GET"], type="http", auth="public")
    @add_guest_to_context
    def discuss_channel(self, channel_id, *, highlight_message_id=None):
        # highlight_message_id is used JS side by parsing the query string
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_public_template(Store(), channel)

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

    def _response_discuss_channel_invitation(self, store, channel, guest_email=None):
        # group restriction takes precedence over token
        # sudo - res.groups: can access group public id of parent channel to determine if we
        # can access the channel.
        group_public_id = channel.group_public_id or channel.parent_channel_id.sudo().group_public_id
        if group_public_id and group_public_id not in request.env.user.all_group_ids:
            raise request.not_found()
        guest_already_known = channel.env["mail.guest"]._get_guest_from_context()
        with replace_exceptions(UserError, by=NotFound()):
            # sudo: mail.guest - creating a guest and its member inside a channel of which they have the token
            __, guest = channel.sudo()._find_or_create_persona_for_channel(
                guest_name=guest_email if guest_email else _("Guest"),
                country_code=request.geoip.country_code,
                timezone=request.env["mail.guest"]._get_timezone_from_request(request),
            )
        if guest_email and not guest.email:
            # sudo - mail.guest: writing email address of self guest is allowed
            guest.sudo().email = guest_email
        if guest and not guest_already_known:
            store.add_global_values(is_welcome_page_displayed=True)
            channel = channel.with_context(guest=guest)
        return self._response_discuss_public_template(store, channel)

    def _response_discuss_public_template(self, store: Store, channel):
        store.add_global_values(
            companyName=request.env.company.name,
            inPublicPage=True,
        )
        store.add_singleton_values("DiscussApp", {"thread": store.One(channel)})
        return request.render(
            "mail.discuss_public_channel_template",
            {
                "data": store.get_result(),
                "session_info": channel.env["ir.http"].session_info(),
            },
        )
