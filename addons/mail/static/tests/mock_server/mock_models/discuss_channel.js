import { Store } from "@mail/../tests/mock_server/store";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { markup } from "@odoo/owl";

import {
    Command,
    fields,
    getKwArgs,
    makeKwArgs,
    models,
    serverState,
} from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";

const { DateTime } = luxon;

export class DiscussChannel extends models.ServerModel {
    _name = "discuss.channel";
    _inherit = ["mail.thread"];
    _mail_post_access = "read";

    author_id = fields.Many2one({
        relation: "res.partner",
        default: () => serverState.partnerId,
    });
    avatar_cache_key = fields.Char({ string: "Avatar Cache Key" });
    channel_member_ids = fields.One2many({
        relation: "discuss.channel.member",
        relation_field: "channel_id",
        string: "Members",
        default: () => [Command.create({ partner_id: serverState.partnerId })],
    });
    channel_name_member_ids = fields.One2many({
        relation: "discuss.channel.member",
        compute: "_compute_channel_name_member_ids",
    });
    channel_type = fields.Generic({ default: "channel" });
    discuss_category_id = fields.Many2one({
        relation: "discuss.category",
        string: "Discuss Category",
    });
    group_public_id = fields.Generic({
        default: () => serverState.groupId,
    });
    invited_member_ids = fields.One2many({
        relation: "discuss.channel.member",
        compute: "_compute_invited_member_ids",
    });
    is_readonly = fields.Boolean({ string: "Read-only" });
    self_member_id = fields.Many2one({
        relation: "discuss.channel.member",
        compute: "_compute_self_member_id",
    });
    uuid = fields.Generic({
        default: () => uniqueId("discuss.channel_uuid-"),
    });
    last_interest_dt = fields.Datetime({ string: "Last Interest" });

    create(vals) {
        // py: a sub-channel always shares its parent's channel_type (enforced by a SQL constraint
        // and set by _create_sub_channel). Mirror that so sub-threads of a group/chat are not
        // mistakenly typed as plain "channel".
        for (const v of Array.isArray(vals) ? vals : [vals]) {
            if (v && v.parent_channel_id && !v.channel_type) {
                const [parent] = this.browse(v.parent_channel_id);
                if (parent) {
                    v.channel_type = parent.channel_type;
                }
            }
        }
        return super.create(...arguments);
    }

    _compute_channel_name_member_ids() {
        for (const channel of this) {
            const members = channel.channel_member_ids ?? [];
            members.sort();
            channel.channel_name_member_ids = members.slice(0, 3);
        }
    }

    _compute_invited_member_ids() {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        for (const channel of this) {
            channel.invited_member_ids = DiscussChannelMember.search([
                ["channel_id", "=", channel.id],
                ["rtc_inviting_session_id", "!=", false],
            ]);
        }
    }

    _compute_self_member_id() {
        for (const channel of this) {
            channel.self_member_id = this._find_or_create_member_for_self(channel.id)?.id ?? false;
        }
    }

    /** @param {number[]} ids */
    action_unfollow(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [channel] = this.browse(ids);
        if (!["channel", "group", "im_livechat", "whatsapp"].includes(channel.channel_type)) {
            const memberIds = this.env["discuss.channel.member"].search([
                ["channel_id", "=", channel.id],
                ["is_self", "=", true],
            ]);
            this.env["discuss.channel.member"]._channel_pin(memberIds, false);
        }
        const custom_store = new Store().add(this.browse(channel.id), {
            close_chat_window: true,
            isLocallyPinned: false,
        });
        const [partner] = ResPartner.read(this.env.user.partner_id);
        const [channelMember] = DiscussChannelMember._filter([
            ["channel_id", "in", ids],
            ["partner_id", "=", this.env.user.partner_id],
        ]);
        BusBus._sendone(partner, "mail.record/insert", custom_store.as_dict());
        if (!channelMember) {
            return true;
        }
        this.write([channel.id], {
            channel_member_ids: [Command.delete(channelMember.id)],
        });
        this.message_post(
            channel.id,
            makeKwArgs({
                author_id: serverState.partnerId,
                body: '<div class="o_mail_notification">left the channel</div>',
                subtype_xmlid: "mail.mt_comment",
            })
        );
        const store = new Store().add(this.browse(channel.id), (res) => {
            res.many("channel_member_ids", [], {
                mode: "DELETE",
                value: DiscussChannelMember.browse(channelMember.id),
            });
            res.attr("member_count", () =>
                DiscussChannelMember.search_count([["channel_id", "=", channel.id]])
            );
        });
        BusBus._sendone(channel, "mail.record/insert", store.as_dict());
        // limitation of mock server, partner already unsubscribed from channel
        BusBus._sendone(partner, "mail.record/insert", store.as_dict());
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partner_ids
     * @param {number[]} user_ids
     * @param {boolean} [invite_to_rtc_call=undefined]
     */
    _add_members(ids, partner_ids, user_ids, invite_to_rtc_call) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids", "user_ids", "invite_to_rtc_call");
        ids = kwargs.ids;
        delete kwargs.ids;
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        partner_ids = [...(kwargs.partner_ids || [])];
        for (const userId of kwargs.user_ids || []) {
            const [user] = ResUsers.browse(userId);
            if (user) {
                partner_ids.push(user.partner_id);
            }
        }

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [channel] = this.browse(ids);
        const partners = ResPartner.browse(partner_ids);
        for (const partner of partners) {
            if (partner.id === this.env.user.partner_id) {
                continue; // adding 'yourself' to the conversation is handled below
            }
            const body = `<div class="o_mail_notification">invited ${partner.name} to the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, makeKwArgs({ body, message_type, subtype_xmlid }));
        }
        const [lastMessageId = 0] = MailMessage.search(
            [
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channel.id],
            ],
            makeKwArgs({ limit: 1, order: "id DESC" })
        );
        const insertedChannelMembers = [];
        for (const partner of partners) {
            const channelMember = DiscussChannelMember.create({
                channel_id: channel.id,
                partner_id: partner.id,
                create_uid: this.env.uid,
                new_message_separator: lastMessageId + 1,
            });
            insertedChannelMembers.push(channelMember);
            BusBus._sendone(partner, "discuss.channel/joined", {
                channel_id: channel.id,
                store_data: new Store()
                    .add(this.browse(channel.id), "_store_channel_fields")
                    .add(DiscussChannelMember.browse(channelMember), ["unpin_dt"])
                    .as_dict(),
                invited_by_user_id: this.env.uid,
            });
        }
        const selfPartner = partners.find((partner) => partner.id === this.env.user.partner_id);
        if (selfPartner) {
            // needs to be done after adding 'self' as a member
            const body = `<div class="o_mail_notification">${selfPartner.name} joined the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, makeKwArgs({ body, message_type, subtype_xmlid }));
        }
        if (insertedChannelMembers.length) {
            BusBus._sendone(
                channel,
                "mail.record/insert",
                new Store()
                    .add(this.browse(channel.id), (res) =>
                        res.attr("member_count", () =>
                            DiscussChannelMember.search_count([["channel_id", "=", channel.id]])
                        )
                    )
                    .add(
                        DiscussChannelMember.browse(insertedChannelMembers),
                        "_store_member_fields"
                    )
                    .as_dict()
            );
        }
        if (kwargs.invite_to_rtc_call) {
            BusBus._sendone(
                channel,
                "mail.record/insert",
                new Store()
                    .add(this.browse(channel.id), (res) =>
                        res.many("invited_member_ids", [], {
                            mode: "ADD",
                            value: DiscussChannelMember.browse(insertedChannelMembers),
                        })
                    )
                    .as_dict()
            );
        }
        return DiscussChannelMember.browse(insertedChannelMembers);
    }

    /**
     * @param {number[]} ids
     * @param {string} description
     */
    channel_change_description(ids, description) {
        const kwargs = getKwArgs(arguments, "ids", "description");
        ids = kwargs.ids;
        delete kwargs.ids;
        description = kwargs.description || "";

        const [channel] = this.browse(ids);
        this.write([channel.id], { description });
    }

    unlink(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const channels = this.browse(ids);
        for (const channel of channels) {
            BusBus._sendone(channel, "discuss.channel/delete", { id: channel.id });
        }
        return super.unlink(...arguments);
    }

    /**
     * @param {string} name
     * @param {string} [group_id]
     */
    _create_channel(name, group_id, is_readonly) {
        const kwargs = getKwArgs(arguments, "name", "group_id", "is_readonly");
        name = kwargs.name;
        group_id = kwargs.group_id;
        is_readonly = kwargs.is_readonly || false;

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const id = this.create({
            channel_member_ids: [Command.create({ partner_id: this.env.user.partner_id })],
            channel_type: "channel",
            name,
            group_public_id: group_id,
            is_readonly,
        });
        this.write([id], { group_public_id: group_id });
        this.message_post(
            id,
            makeKwArgs({
                body: `<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="${id}">#${name}</a></div>`,
                message_type: "notification",
            })
        );
        this._broadcast([id], [this.env.user.id]);
        return DiscussChannel.browse(id);
    }

    _channel_basic_info_fields() {
        return [
            "avatar_cache_key",
            "channel_type",
            "create_date",
            "create_uid",
            "default_display_mode",
            "description",
            "group_public_id",
            "is_readonly",
            "last_interest_dt",
            "name",
            "uuid",
        ];
    }

    /** @param {number[]} ids */
    _channel_basic_info(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const [data] = this._read_format(ids, this._channel_basic_info_fields(), false);
        const [channel] = this.browse(ids);
        const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
        Object.assign(data, {
            is_editable: (() => {
                if (channel.channel_type === "channel") {
                    // Match the ACL rules
                    return (
                        !channel.group_public_id ||
                        this.env.user.group_ids.includes(channel.group_public_id)
                    );
                }
                return Boolean(memberOfCurrentUser);
            })(),
            group_ids: channel.group_ids,
            member_count: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
        });
        return data;
    }

    /**
     * @param {number[]} partners_to
     */
    _get_or_create_chat(partners_to) {
        const kwargs = getKwArgs(arguments, "partners_to");
        partners_to = kwargs.partners_to || [];

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (!partners_to.includes(this.env.user.partner_id)) {
            partners_to.push(this.env.user.partner_id);
        }
        const partners = ResPartner.browse(partners_to);
        const channels = this.search_read([["channel_type", "=", "chat"]]);
        for (const channel of channels) {
            const channelMemberIds = DiscussChannelMember.search([
                ["channel_id", "=", channel.id],
                ["partner_id", "in", partners_to],
            ]);
            if (
                channelMemberIds.length === partners.length &&
                channel.channel_member_ids.length === partners.length
            ) {
                return DiscussChannel.browse(channel.id);
            }
        }
        const id = this.create({
            channel_member_ids: partners.map((partner) =>
                Command.create({
                    partner_id: partner.id,
                    unpin_dt:
                        partner.id == serverState.partnerId ? false : serializeDateTime(today()),
                })
            ),
            channel_type: "chat",
            name: partners.map((partner) => partner.name).join(", "),
        });
        this._broadcast(
            [id],
            partners.flatMap((partner) => partner.user_ids)
        );
        return DiscussChannel.browse(id);
    }

    _store_rtc_update_fields(res, { added, removed } = {}) {
        if (added) {
            res.many("rtc_session_ids", "_store_rtc_session_fields", { mode: "ADD", value: added });
        }
        if (removed) {
            res.many("rtc_session_ids", [], { mode: "DELETE", value: removed });
        }
    }

    _store_channel_fields(res) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        const bus_last_id = BusBus.lastBusNotificationId;
        const isChannel = (channel) => channel.channel_type === "channel";
        const isChannelOrGroup = (channel) => ["channel", "group"].includes(channel.channel_type);
        // mock: keep the relational computes fresh, mirroring `self.fetch(["self_member_id"])`.
        this._compute_self_member_id();
        this._compute_invited_member_ids();
        res.attr("avatar_cache_key", undefined, { predicate: isChannelOrGroup });
        res.attr("avatar_128_access_token", (c) => c.id, { predicate: isChannelOrGroup });
        // sudo: discuss.category - guests can read categories of accessible channels
        res.one("discuss_category_id", "_store_category_fields", { sudo: true });
        res.attr("channel_type");
        res.attr("create_uid");
        res.attr("create_date", undefined, {
            predicate: (channel) =>
                channel.default_display_mode === "video_full_screen" || channel.parent_channel_id,
        });
        res.many("channel_member_ids", "_store_member_fields", {
            only_data: true,
            sort: "id",
            predicate: (channel) =>
                !this._lazy_load_members_channel_types().includes(channel.channel_type),
        });
        res.attr("default_display_mode");
        res.attr("description", undefined, { predicate: isChannelOrGroup });
        res.one("from_message_id", "_store_message_fields", { predicate: isChannelOrGroup });
        // sudo: we are reading only the ids (comodel is inaccessible)
        res.many("group_ids", [], { predicate: isChannel, sudo: true });
        res.one("group_public_id", ["full_name"], { predicate: isChannel });
        res.many("invited_member_ids", "_store_avatar_card_fields", { mode: "ADD" });
        res.attr("is_readonly", undefined, { predicate: isChannel });
        res.attr("last_interest_dt");
        res.attr("member_count", (channel) =>
            DiscussChannelMember.search_count([["channel_id", "=", channel.id]])
        );
        res.attr(
            "message_count",
            (channel) =>
                MailMessage.search_count([
                    ["model", "=", "discuss.channel"],
                    ["res_id", "=", channel.id],
                    ["message_type", "not in", ["user_notification", "notification"]],
                ]),
            { predicate: (channel) => channel.parent_channel_id }
        );
        res.attr("name");
        res.many("channel_name_member_ids", "_store_member_fields", {
            sort: "id",
            predicate: (channel) =>
                this._member_based_naming_channel_types().includes(channel.channel_type),
        });
        res.one("parent_channel_id", "_store_channel_fields", { predicate: isChannelOrGroup });
        // sudo: discuss.channel: reading sessions of accessible channel is acceptable
        res.many("rtc_session_ids", "_store_extra_fields", { mode: "ADD", sudo: true });
        res.attr("uuid");
        if (res.is_for_current_user()) {
            res.attr("fetchChannelInfoState", "fetched");
            res.attr("is_editable", (channel) => {
                if (channel.channel_type === "channel") {
                    // Match the ACL rules
                    return (
                        !channel.group_public_id ||
                        this.env.user.group_ids.includes(channel.group_public_id)
                    );
                }
                return Boolean(this._find_or_create_member_for_self(channel.id));
            });
            res.attr("message_needaction_counter", (channel) => {
                if (!this.env.user) {
                    return 0;
                }
                const messages = MailMessage._filter([
                    ["model", "=", "discuss.channel"],
                    ["res_id", "=", channel.id],
                ]);
                return MailNotification._filter([
                    ["res_partner_id", "=", this.env.user.partner_id],
                    ["is_read", "=", false],
                    ["mail_message_id", "in", messages.map((message) => message.id)],
                ]).length;
            });
            res.attr("message_needaction_counter_bus_id", bus_last_id);
            for (const channel of this) {
                const member = this._find_or_create_member_for_self(channel.id);
                if (member) {
                    DiscussChannelMember._compute_message_unread_counter();
                }
            }
            res.one(
                "self_member_id",
                (memberRes) => {
                    memberRes.from_method("_store_member_fields");
                    memberRes.extend(["custom_notifications"]);
                    memberRes.extend(["last_interest_dt", "message_unread_counter"]);
                    memberRes.attr("message_unread_counter_bus_id", bus_last_id);
                    memberRes.extend(["mute_until_dt", "new_message_separator"]);
                    // sudo: discuss.channel.rtc.session - each member can see who is inviting them
                    memberRes.one("rtc_inviting_session_id", "_store_rtc_session_fields", {
                        sudo: true,
                    });
                    memberRes.attr("unpin_dt");
                },
                { only_data: true }
            );
        }
    }

    _store_open_chat_window_fields(res) {
        this._store_channel_fields(res);
        res.attr("open_chat_window", true);
    }

    _store_message_update_extra_fields(res) {
        res.one("parent_id", "_store_message_fields");
    }

    _member_based_naming_channel_types() {
        return ["group"];
    }

    _lazy_load_members_channel_types() {
        return ["channel", "group"];
    }

    /**
     * @param {number[]} ids
     * @param {string} name
     */
    channel_rename(ids, name) {
        const kwargs = getKwArgs(arguments, "ids", "name");
        ids = kwargs.ids;
        delete kwargs.ids;
        name = kwargs.name || "";

        const [channel] = this.browse(ids);
        this.write([channel.id], { name });
        this.message_post(
            channel.id,
            makeKwArgs({
                body: `<div data-oe-type="channel_rename" class="o_mail_notification">${name}</div>`,
                message_type: "notification",
                subtype_xmlid: "mail.mt_comment",
            })
        );
    }

    /**
     * @param {number[]} ids
     * @param {string} name
     */
    /**
     * @param {number[]} users_to
     * @param {string} [default_display_mode=undefined]
     * @param {string} name
     * */
    _create_group(users_to, default_display_mode, name) {
        const kwargs = getKwArgs(arguments, "users_to", "default_display_mode", "name");
        users_to = kwargs.users_to || [];
        default_display_mode = kwargs.default_display_mode;
        name = kwargs.name || "";

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const users = ResUsers.browse(users_to);
        const id = this.create({
            channel_type: "group",
            channel_member_ids: users.map((user) =>
                Command.create({ partner_id: user.partner_id })
            ),
            default_display_mode,
            name,
        });
        this._broadcast([id], users);
        return DiscussChannel.browse(id);
    }

    _create_sub_channel(ids, from_message_id, name) {
        const kwargs = getKwArgs(arguments, "ids", "from_message_id", "name");
        ids = kwargs.ids;
        from_message_id = kwargs.from_message_id;
        name = kwargs.name;
        delete kwargs.name;
        delete kwargs.ids;
        delete kwargs.from_message_id;
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        const self = this.browse(ids)[0];
        let message;
        if (from_message_id) {
            [message] = MailMessage.browse(from_message_id);
        }
        const [partner] = ResPartner._get_current_persona();
        const subChannels = this.browse(
            this.create({
                channel_member_ids: [Command.create({ partner_id: partner.id })],
                channel_type: "channel",
                group_public_id: self.group_public_id,
                from_message_id: message?.id,
                name: message
                    ? convertBrToLineBreak(markup(message.body)).substring(0, 30)
                    : name || "New Thread",
                parent_channel_id: self.id,
            })
        );
        const store = new Store().add(subChannels, "_store_channel_fields");
        BusBus._sendone(partner, "mail.record/insert", store.as_dict());
        this.message_post(
            self.id,
            makeKwArgs({
                body: `${partner.display_name} started a thread: <a href='#' class='o_channel_redirect' data-oe-id='${subChannels[0].id}' data-oe-model='discuss.channel'>${subChannels[0].name}</a>.`,
                message_type: "notification",
                subtype_xmlid: "mail.mt_comment",
            })
        );
        return {
            store_data: store.as_dict(),
            sub_channel: subChannels[0].id,
        };
    }

    /** @param {number} id */
    execute_command_help(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const id = ids[0];
        const [channel] = this.search_read([["id", "=", id]]);
        const notifBody = /* html */ `
            <span class="o_mail_notification">You are in ${
                channel.channel_type === "channel" ? "" : "a private conversation with"
            }
            <b>${
                channel.channel_type === "channel"
                    ? `#${channel.name}`
                    : channel.channel_member_ids.map(
                          (id) => DiscussChannelMember.search_read([["id", "=", id]])[0].name
                      )
            }</b>.<br><br>

            <b>@username</b> to mention someone<br>
            <b>@role</b> to notify multiple people<br>
            <b>/command</b> to run a command<br>
            <b>::shortcut</b> to insert a canned response<br>
            <b>:emoji:</b> to insert an emoji</span>
        `;
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "discuss.channel/transient_message", {
            body: notifBody,
            channel_id: channel.id,
        });
        return true;
    }

    /** @param {number[]} ids */
    execute_command_who(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const channels = this.browse(ids);
        for (const channel of channels) {
            const members = DiscussChannelMember.browse(channel.channel_member_ids);
            const otherPartnerIds = members
                .filter(
                    (member) => member.partner_id && member.partner_id !== this.env.user.partner_id
                )
                .map((member) => member.partner_id);
            const otherPartners = ResPartner.browse(otherPartnerIds);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners
                    .map((partner) => partner.name)
                    .join(", ")} and you`;
            }
            const [partner] = ResPartner.read(this.env.user.partner_id);
            BusBus._sendone(partner, "discuss.channel/transient_message", {
                body: `<span class="o_mail_notification">${message}</span>`,
                channel_id: channel.id,
            });
        }
    }

    get_channels_as_member() {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const guest = MailGuest._get_guest_from_context();
        const memberDomain = guest
            ? [["guest_id", "=", guest.id]]
            : [["partner_id", "=", this.env.user.partner_id]];
        const members = DiscussChannelMember._filter(memberDomain);
        const pinnedMembers = members.filter((member) => member.is_pinned);
        const channels = this._filter([
            ["channel_type", "in", ["channel", "group"]],
            ["channel_member_ids", "in", members.map((member) => member.id)],
        ]);
        const pinnedChannels = this._filter([
            ["channel_type", "not in", ["channel", "group"]],
            ["channel_member_ids", "in", pinnedMembers.map((member) => member.id)],
        ]);
        return [...channels, ...pinnedChannels];
    }

    /** @param {number} id */
    message_post(id) {
        const kwargs = getKwArgs(arguments, "id");
        id = kwargs.id;
        delete kwargs.id;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        kwargs.message_type ||= "notification";
        const [channel] = this.browse(id);
        this.write([id], {
            last_interest_dt: serializeDateTime(DateTime.now()),
        });
        if (kwargs.special_mentions?.includes("everyone")) {
            kwargs["partner_ids"] = DiscussChannelMember._filter([
                ["channel_id", "=", channel.id],
            ]).map((member) => member.partner_id);
        }
        delete kwargs.special_mentions;
        const messageIds = MailThread.message_post.call(this, [id], kwargs);
        // simulate compute of message_unread_counter
        const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
        const otherMembers = DiscussChannelMember._filter([
            ["channel_id", "=", channel.id],
            ["id", "!=", memberOfCurrentUser?.id || false],
        ]);
        for (const member of otherMembers) {
            DiscussChannelMember.write([member.id], {
                message_unread_counter: member.message_unread_counter + 1,
            });
        }
        return messageIds;
    }

    /**
     * @param {number} id
     * @param {number} message_id
     * @param {boolean} pinned
     */
    set_message_pin(id, message_id, pinned) {
        const kwargs = getKwArgs(arguments, "id", "message_id", "pinned");
        id = kwargs.id;
        delete kwargs.id;
        message_id = kwargs.message_id;
        pinned = kwargs.pinned;

        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        MailThread.set_message_pin.call(this, id, message_id, pinned);
        const [partner] = ResPartner.read(this.env.user.partner_id);
        const notification = `<div data-oe-type="pin" class="o_mail_notification">
                ${partner.display_name} pinned a
                <a href="#" data-oe-type="highlight" data-oe-id='${message_id}'>message</a> to this channel.
                <a href="#" data-oe-type="pin-menu">See all pinned messages</a>
            </div>`;
        this.message_post(
            id,
            makeKwArgs({
                body: notification,
                message_type: "notification",
                subtype_xmlid: "mail.mt_comment",
            })
        );
    }

    /** @type {typeof models.Model["prototype"]["write"]} */
    write(idOrIds, values) {
        const kwargs = getKwArgs(arguments, "ids", "vals");
        ({ ids: idOrIds, vals: values } = kwargs);

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const channels = this.browse(ensureArray(idOrIds));
        const basicInfoByChannelId = Object.fromEntries(
            channels.map((channel) => [channel.id, this._channel_basic_info(channel.id)])
        );
        for (const channel of channels) {
            if ("image_128" in values) {
                super.write(channel.id, {
                    avatar_cache_key: DateTime.utc().toFormat("yyyyMMddHHmmss"),
                });
            }
        }
        const result = super.write(...arguments);
        const notifications = [];
        for (const channel of channels) {
            const basicInfo = this._channel_basic_info(channel.id);
            const previousBasicInfo = basicInfoByChannelId[channel.id];
            const changes = [];
            for (const key of Object.keys(basicInfo)) {
                if (basicInfo[key] !== previousBasicInfo[key]) {
                    changes.push([key, basicInfo[key]]);
                }
            }
            if (changes.length) {
                notifications.push([
                    channel,
                    "mail.record/insert",
                    new Store().add(this.browse(channel.id), Object.fromEntries(changes)).as_dict(),
                ]);
            }
        }
        if (notifications.length) {
            BusBus._sendmany(notifications);
        }
        return result;
    }

    /**
     * @param {number[]} ids
     * @param {number[]} user_ids
     */
    _broadcast(ids, user_ids) {
        const kwargs = getKwArgs(arguments, "ids", "user_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        user_ids = kwargs.user_ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const notifications = this._channel_channel_notifications(ids, user_ids);
        BusBus._sendmany(notifications);
    }

    /**
     * @param {number} id
     * @param {number[]} user_ids
     */
    _channel_channel_notifications(ids, user_ids) {
        const kwargs = getKwArgs(arguments, "ids", "user_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        user_ids = kwargs.user_ids;

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const notifications = [];
        for (const user_id of user_ids) {
            const user = ResUsers.browse(user_id)[0];
            if (!user) {
                continue;
            }
            // Note: `_store_channel_fields` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const [relatedPartner] = ResPartner.search_read([["id", "=", user.partner_id]]);
            for (const channelId of ids) {
                notifications.push([
                    relatedPartner,
                    "mail.record/insert",
                    new Store()
                        .add(DiscussChannel.browse(channelId), "_store_channel_fields")
                        .as_dict(),
                ]);
            }
        }
        return notifications;
    }

    _types_allowing_seen_infos() {
        return ["chat", "group"];
    }

    _get_channels_as_member() {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const guest = MailGuest._get_guest_from_context();
        const memberDomain = guest
            ? [["guest_id", "=", guest.id]]
            : [["partner_id", "=", this.env.user.partner_id]];
        const members = DiscussChannelMember._filter(memberDomain);
        const pinnedMembers = members.filter((member) => member.is_pinned);
        return this._filter([
            ["channel_member_ids", "in", pinnedMembers.map((member) => member.id)],
        ]);
    }

    /**
     * @param {number} id
     * @returns {import("mock_models").DiscussChannelMember}
     */
    _find_or_create_member_for_self(id) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [partner, guest] = ResPartner._get_current_persona();
        if (!partner && !guest) {
            return;
        }
        return DiscussChannelMember._filter([
            ["channel_id", "=", id],
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", partner.id],
        ])[0];
    }

    _find_or_create_persona_for_channel(id, guest_name) {
        const kwargs = getKwArgs(arguments, "id", "guest_name");
        id = kwargs.id;
        delete kwargs.id;
        guest_name = kwargs.guest_name;

        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        if (this._find_or_create_member_for_self(id)) {
            return;
        }
        const guestId =
            MailGuest._get_guest_from_context()?.id ?? MailGuest.create({ name: guest_name });
        this.write([id], {
            channel_member_ids: [Command.create({ guest_id: guestId })],
        });
        MailGuest._set_auth_cookie(guestId);
    }
}
