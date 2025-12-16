# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store, add_guest_to_context
from odoo.exceptions import AccessError


class DiscussChannelWebclientController(WebclientController):
    """Override to add discuss channel specific features."""

    @classmethod
    def _process_request_loop(self, store: Store, fetch_params):
        """Override to add discuss channel specific features."""
        # aggregate of channels to return, to batch them in a single query when all the fetch params
        # have been processed
        request.update_context(
            channels=request.env["discuss.channel"], add_channels_last_message=False
        )
        super()._process_request_loop(store, fetch_params)
        channels = request.env.context["channels"]
        if channels:
            store.add(channels, "_store_channel_fields")
            store.add(channels.self_member_id, ["is_favorite"])
        if request.env.context["add_channels_last_message"]:
            # fetch channels data before messages to benefit from prefetching (channel info might
            # prefetch a lot of data that message format could use)
            store.add(channels._get_last_messages(), "_store_message_fields")

    @classmethod
    def _process_request_for_all(self, store: Store, name, params):
        """Override to return channel as member and last messages."""
        super()._process_request_for_all(store, name, params)
        if name == "init_messaging":
            member_domain = [("is_self", "=", True), ("rtc_inviting_session_id", "!=", False)]
            channel_domain = [("channel_member_ids", "any", member_domain)]
            channels = request.env["discuss.channel"].search_fetch(channel_domain)
            request.update_context(channels=request.env.context["channels"] | channels)
        if name == "channels_as_member":
            channels = request.env["discuss.channel"]._get_channels_as_member()
            request.update_context(
                channels=request.env.context["channels"] | channels, add_channels_last_message=True
            )
        if name == "discuss.channel":
            channels = request.env["discuss.channel"].search([("id", "in", params)])
            request.update_context(channels=request.env.context["channels"] | channels)
        if name == "/discuss/channel/favorite":
            if member := request.env["discuss.channel.member"].search(
                [("channel_id", "=", params["channel_id"]), ("is_self", "=", True)],
            ):
                member.is_favorite = params["is_favorite"]
        resolve_channel = request.env["discuss.channel"]
        if name == "/discuss/get_or_create_chat":
            resolve_channel = request.env["discuss.channel"]._get_or_create_chat(
                params["partners_to"],
            )
        if name == "/discuss/create_channel":
            resolve_channel = request.env["discuss.channel"]._create_channel(
                params["name"],
                params["group_id"],
            )
        if name == "/discuss/create_group":
            resolve_channel = request.env["discuss.channel"]._create_group(
                params["partners_to"],
                params.get("default_display_mode", False),
                params.get("name", ""),
            )
        store.resolve_data_request(
            lambda res: res.one("channel", "_store_channel_fields", value=resolve_channel),
        )

    @classmethod
    def _store_init_messaging_global_fields(cls, res: Store.FieldList, bus_last_id):
        channels = request.env["discuss.channel"]._get_channels_as_member()
        members = request.env["discuss.channel.member"].search_fetch(
            [("channel_id", "in", channels.ids), ("is_self", "=", True)],
        )
        members_with_unread = members.filtered(lambda member: member.message_unread_counter)
        res.attr("initChannelsUnreadCounter", len(members_with_unread))
        # fetch channels data before calling super to benefit from prefetching (channel info might
        # prefetch a lot of data that super could use, about the current user in particular)
        super()._store_init_messaging_global_fields(res, bus_last_id)


class ChannelController(http.Controller):
    @http.route("/discuss/channel/members", methods=["POST"], type="jsonrpc", auth="public", readonly=True)
    @add_guest_to_context
    def discuss_channel_members(self, channel_id, known_member_ids):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        unknown_members = self.env["discuss.channel.member"].search(
            domain=[("id", "not in", known_member_ids), ("channel_id", "=", channel.id)],
            limit=100,
        )
        store = Store()
        store.add(channel, ["member_count"])
        store.add(unknown_members, "_store_member_fields")
        return store.get_result()

    @http.route("/discuss/channel/update_avatar", methods=["POST"], type="jsonrpc")
    def discuss_channel_avatar_update(self, channel_id, data):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel or not data:
            raise NotFound()
        channel.write({"image_128": data})

    @http.route("/discuss/channel/messages", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def discuss_channel_messages(self, channel_id, fetch_params=None):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        res = request.env["mail.message"]._message_fetch(domain=None, thread=channel, **(fetch_params or {}))
        messages = res.pop("messages")
        if not request.env.user._is_public():
            messages.set_message_done()
        store = Store().add(messages, "_store_message_fields")
        return {**res, "data": store.get_result(), "messages": messages.ids}

    @http.route("/discuss/channel/mark_as_read", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def discuss_channel_mark_as_read(self, channel_id, last_message_id):
        member = request.env["discuss.channel.member"].search([
            ("channel_id", "=", channel_id),
            ("is_self", "=", True),
        ])
        if not member:
            return  # ignore if the member left in the meantime
        member._mark_as_read(last_message_id)

    @http.route("/discuss/channel/set_new_message_separator", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def discuss_channel_set_new_message_separator(self, channel_id, message_id):
        member = request.env["discuss.channel.member"].search([
            ("channel_id", "=", channel_id),
            ("is_self", "=", True),
        ])
        if not member:
            raise NotFound()
        return member._set_new_message_separator(message_id)

    @http.route("/discuss/channel/notify_typing", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def discuss_channel_notify_typing(self, channel_id, is_typing):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise request.not_found()
        if is_typing:
            member = channel._find_or_create_member_for_self()
        else:
            # Do not create member automatically when setting typing to `False`
            # as it could be resulting from the user leaving.
            member = request.env["discuss.channel.member"].search(
                [
                    ("channel_id", "=", channel_id),
                    ("is_self", "=", True),
                ]
            )
        if member:
            member._notify_typing(is_typing)

    @http.route("/discuss/channel/attachments", methods=["POST"], type="jsonrpc", auth="public", readonly=True)
    @add_guest_to_context
    def load_attachments(self, channel_id, limit=30, before=None):
        """Load attachments of a channel. If before is set, load attachments
        older than the given id.
        :param channel_id: id of the channel
        :param limit: maximum number of attachments to return
        :param before: id of the attachment from which to load older attachments
        """
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        domain = [
            ["res_id", "=", channel_id],
            ["res_model", "=", "discuss.channel"],
        ]
        if before:
            domain.append(["id", "<", before])
        # sudo: ir.attachment - reading attachments of a channel that the current user can access
        attachments = request.env["ir.attachment"].sudo().search(domain, limit=limit, order="id DESC")
        store = Store().add(attachments, "_store_attachment_fields")
        return {"store_data": store.get_result(), "count": len(attachments)}

    @http.route("/discuss/channel/join", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def discuss_channel_join(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        channel._find_or_create_member_for_self()
        return Store().add(channel, "_store_channel_fields").get_result()

    @http.route("/discuss/channel/sub_channel/create", methods=["POST"], type="jsonrpc", auth="public")
    def discuss_channel_sub_channel_create(self, parent_channel_id, from_message_id=None, name=None):
        channel = request.env["discuss.channel"].search([("id", "=", parent_channel_id)])
        if not channel:
            raise NotFound()
        sub_channel = channel._create_sub_channel(from_message_id, name)
        store = Store().add(sub_channel, "_store_channel_fields")
        return {"store_data": store.get_result(), "sub_channel": sub_channel.id}

    @http.route("/discuss/channel/sub_channel/fetch", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def discuss_channel_sub_channel_fetch(self, parent_channel_id, search_term=None, before=None, limit=30):
        channel = request.env["discuss.channel"].search([("id", "=", parent_channel_id)])
        if not channel:
            raise NotFound()
        domain = [("parent_channel_id", "=", channel.id)]
        if before:
            domain.append(("id", "<", before))
        if search_term:
            domain.append(("name", "ilike", search_term))
        sub_channels = request.env["discuss.channel"].search(domain, order="id desc", limit=limit)
        store = Store()
        store.add(sub_channels, "_store_channel_fields")
        store.add(sub_channels._get_last_messages(), "_store_message_fields")
        if sub_channels:
            self.env.cr.execute(
                """
                    SELECT id
                      FROM (
                          SELECT id,
                                  ROW_NUMBER() OVER (PARTITION BY channel_id ORDER BY id) AS rn
                            FROM discuss_channel_member
                           WHERE channel_id IN %s
                      )
                     WHERE rn <= 4;
                """,
                (tuple(sub_channels.ids),),
            )
            store.add(
                self.env["discuss.channel.member"].browse([r[0] for r in self.env.cr.fetchall()]),
                "_store_member_fields",
            )
        return {
            "store_data": store.get_result(),
            "sub_channel_ids": sub_channels.ids,
        }

    @http.route("/discuss/channel/sub_channel/delete", methods=["POST"], type="jsonrpc", auth="user")
    def discuss_delete_sub_channel(self, sub_channel_id):
        channel = request.env["discuss.channel"].search_fetch([("id", "=", sub_channel_id)])
        if not channel or not channel.parent_channel_id or channel.create_uid != request.env.user:
            raise NotFound()
        body = Markup('<div class="o_mail_notification" data-oe-type="thread_deletion">%s</div>') % channel.name
        channel.parent_channel_id.message_post(body=body, subtype_xmlid="mail.mt_comment")
        # sudo: discuss.channel - skipping ACL for users who created the thread
        channel.sudo().unlink()

    @http.route("/discuss/channel/remove_member", methods=["POST"], type="jsonrpc", auth="public")
    def discuss_channel_remove_member(self, member_id):
        channel_member = request.env["discuss.channel.member"].search([("id", "=", member_id)])
        if not channel_member:
            raise NotFound()
        channel_member.unlink()

    @http.route("/discuss/channel/member/set_role", methods=["POST"], type="jsonrpc", auth="public")
    def discuss_channel_set_channel_member_role(self, member_id, channel_role):
        channel_member = request.env["discuss.channel.member"].search([("id", "=", member_id)])
        if not channel_member:
            raise NotFound()
        channel = channel_member.channel_id
        # sudo: discuss.channel.member - reading channel role of is considered allowed
        self_channel_role = channel.self_member_id.sudo().channel_role
        if not self_channel_role == "owner" and not request.env.user.has_group("base.group_system"):
            raise AccessError(self.env._("Only the channel owner or DB admins can modify member roles."))
        if (
            channel_member.sudo().channel_role == "owner"
            and channel_member != channel.self_member_id
            and not request.env.user.has_group("base.group_system")
        ):
            raise AccessError(
                self.env._("Removing ownership from an owner is not allowed. Please contact your DB administrator.")
            )
        # sudo: discuss.channel.member - writing channel role of a member is considered allowed
        channel_member.sudo().channel_role = channel_role
