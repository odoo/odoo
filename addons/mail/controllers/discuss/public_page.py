# Part of Odoo. See LICENSE file for full copyright and licensing details.
import psycopg2.errors
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import email_normalize, replace_exceptions
from odoo.tools.misc import verify_hash_signed
from odoo.addons.mail.tools.discuss import mail_route, Store


class PublicPageController(http.Controller):
    @mail_route(
        [
            "/chat/<string:create_token>",
            "/chat/<string:create_token>/<string:channel_name>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def discuss_channel_chat_from_token(self, create_token, channel_name=None, fullscreen=None):
        return self._response_discuss_channel_from_token(create_token=create_token, channel_name=channel_name)

    @mail_route(
        [
            "/meet/<string:create_token>",
            "/meet/<string:create_token>/<string:channel_name>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def discuss_channel_meet_from_token(self, create_token, channel_name=None, fullscreen=None):
        return self._response_discuss_channel_from_token(
            create_token=create_token, channel_name=channel_name, default_display_mode="video_full_screen"
        )

    def _check_invitation_token(self, channel_id, invitation_token):
        channel = request.env["discuss.channel"].browse(channel_id).exists()
        # sudo: discuss.channel - channel access is validated with invitation_token
        if not channel or not channel._verify_uuid(invitation_token):
            raise NotFound()
        return channel

    @mail_route("/chat/<int:channel_id>/<string:invitation_token>", methods=["GET"], type="http", auth="public")
    def discuss_channel_invitation(self, channel_id, invitation_token, email_token=None, fullscreen=None):
        guest_email = email_token and verify_hash_signed(
            self.env(su=True), "mail.invite_email", email_token
        )
        guest_email = email_normalize(guest_email)
        channel = self._check_invitation_token(channel_id, invitation_token)
        store = Store().add_global_values(isChannelTokenSecret=True)
        return self._response_discuss_channel_invitation(store, channel, guest_email)

    def _check_channel_access(self, channel):
        # group restriction takes precedence over token
        # sudo - res.groups: can access group public id of parent channel to determine if we
        # can access the channel.
        group_public_id = channel.group_public_id or channel.parent_channel_id.sudo().group_public_id
        if group_public_id and group_public_id not in request.env.user.all_group_ids:
            raise request.not_found()

    @mail_route(
        "/chat/<int:channel_id>/<string:invitation_token>/join",
        methods=["POST"],
        type="jsonrpc",
        auth="public",
    )
    def discuss_channel_invitation_join(self, channel_id, invitation_token, guest_name=None):
        user, guest = self.env["res.users"]._get_current_persona()
        if not guest and not user:
            raise NotFound()
        if guest and guest_name and guest.name != guest_name:
            # sudo - mail.guest: writing name of self guest is allowed
            guest.sudo()._update_name(guest_name)
        channel = self._check_invitation_token(channel_id, invitation_token)
        self._check_channel_access(channel)
        store = Store()
        member = channel.sudo()._get_or_create_member_after_invite(guest=guest)
        store.add(member, "_store_member_fields")
        store.add_global_values(
            lambda res: res.one("channel_invitation_pending", [], value=None)
        )
        return store

    @mail_route("/discuss/channel/<int:channel_id>", methods=["GET"], type="http", auth="public")
    def discuss_channel(self, channel_id, *, debug=None, highlight_message_id=None, fullscreen=None):
        # highlight_message_id and fullscreen are used JS side by parsing the query string
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_public_template(Store(), channel)

    @mail_route("/discuss", methods=["GET"], type="http", auth="public")
    def discuss_public(self, *, debug=None, active_id=None):
        _, guest = self.env["res.users"]._get_current_persona()
        if self.env.user._is_public() and not guest:
            raise NotFound()
        return self._response_discuss_public_template(Store())

    def _response_discuss_channel_from_token(self, create_token, channel_name=None, default_display_mode=False):
        # sudo: ir.config_parameter - reading hard-coded key and using it in a simple condition
        if not request.env["ir.config_parameter"].sudo().get_bool("mail.chat_from_token"):
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
        self._check_channel_access(channel)
        guest_already_known = channel.env["mail.guest"]._get_guest_from_context()
        previous_member = None
        if guest_email and not guest_already_known:
            # sudo: discuss.channel.member - searching pending members with sudo to get access rights as guest won't have access to.
            pending_member_sudo = request.env["discuss.channel.member"].sudo().search_fetch(
                [
                    ("channel_id", "=", channel.id),
                    ("invitation_sent_dt", "!=", False),
                    ("guest_id.email", "=", guest_email),
                ],
                limit=1,
            )
            if pending_member_sudo:
                pending_guest_sudo = pending_member_sudo.guest_id
                pending_guest_sudo._set_auth_cookie()
                guest_from_context = pending_guest_sudo.sudo(False)
                channel = channel.with_context(guest=guest_from_context)
        else:
            previous_member = channel.sudo().self_member_id
        with replace_exceptions(UserError, by=NotFound()):
            # sudo: mail.guest - creating a guest and its member inside a channel of which they have the token
            guest = channel.sudo()._get_or_create_guest_for_channel_invite(
                guest_name=guest_email or "",
                country_code=request.geoip.country_code,
                timezone=request.env["mail.guest"]._get_timezone_from_request(request),
            )
        if guest_email and not guest.email:
            # sudo - mail.guest: writing email address of self guest is allowed
            guest.sudo().email = guest_email
        if request.env.user._is_public() and not previous_member:
            store.add_global_values(is_welcome_page_displayed=True)
            channel = channel.with_context(guest=guest)
        if self.env.user._is_internal():
            return request.redirect(f"/odoo/action-mail.action_discuss?active_id={channel.id}&invitation_token={channel.uuid}")
        store.add_global_values(
            lambda res: res.one("channel_invitation_pending", ["uuid", "create_uid"], value=channel.sudo()),
        )
        # sudo: discuss.channel - reading channel fields for the invitation page is allowed,
        # as the guest/user has the invitation token
        return self._response_discuss_public_template(store, channel)

    def _response_discuss_public_template(self, store: Store, channel=None):
        store.add_global_values(
            companyName=request.env.company.name,
            inPublicPage=True,
        )
        if channel:
            self._add_channel_to_store(store, channel)
        return request.render(
            "mail.discuss_public_channel_template",
            {
                "session_info": request.env["ir.http"].session_info(),
                "store_data": store.as_dict(),
            },
        )

    def _add_channel_to_store(self, store: Store, channel):
        # sudo: discuss.channel - reading channel fields for the invitation page is allowed,
        channel_sudo = channel.sudo()
        store.add(channel_sudo, "_store_channel_fields")
        store.add_model_values(
            "DiscussApp",
            lambda res: res.one("thread", [], as_thread=True, value=channel_sudo),
        )
