import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
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
    group_public_id = fields.Generic({
        default: () => serverState.groupId,
    });
    uuid = fields.Generic({
        default: () => uniqueId("discuss.channel_uuid-"),
    });
    last_interest_dt = fields.Datetime({ string: "Last Interest" });

    _compute_channel_name_member_ids() {
        for (const channel of this) {
            const members = channel.channel_member_ids ?? [];
            members.sort();
            channel.channel_name_member_ids = members.slice(0, 3);
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
        const custom_store = new mailDataHelpers.Store(this.browse(channel.id), {
            close_chat_window: true,
            isLocallyPinned: false,
        });
        const [partner] = ResPartner.read(this.env.user.partner_id);
        const [channelMember] = DiscussChannelMember._filter([
            ["channel_id", "in", ids],
            ["partner_id", "=", this.env.user.partner_id],
        ]);
        BusBus._sendone(partner, "mail.record/insert", custom_store.get_result());
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
        const store = new mailDataHelpers.Store(this.browse(channel.id), {
            channel_member_ids: mailDataHelpers.Store.many(
                DiscussChannelMember.browse(channelMember.id),
                makeKwArgs({ only_id: true, mode: "DELETE" })
            ),
            member_count: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
        });
        BusBus._sendone(channel, "mail.record/insert", store.get_result());
        // limitation of mock server, partner already unsubscribed from channel
        BusBus._sendone(partner, "mail.record/insert", store.get_result());
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partner_ids
     * @param {boolean} [invite_to_rtc_call=undefined]
     */
    add_members(ids, partner_ids, invite_to_rtc_call) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids", "invite_to_rtc_call");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
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
        const insertedChannelMembers = [];
        for (const partner of partners) {
            const channelMember = DiscussChannelMember.create({
                channel_id: channel.id,
                partner_id: partner.id,
                create_uid: this.env.uid,
            });
            insertedChannelMembers.push(channelMember);
            BusBus._sendone(partner, "discuss.channel/joined", {
                channel_id: channel.id,
                data: new mailDataHelpers.Store(this.browse(channel.id), {
                    ...this._channel_basic_info([channel.id]),
                    model: "discuss.channel",
                })
                    .add(DiscussChannelMember.browse(channelMember), "unpin_dt")
                    .get_result(),
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
        const isSelfMember =
            DiscussChannelMember.search_count([
                ["partner_id", "=", this.env.user.partner_id],
                ["channel_id", "=", channel.id],
            ]) > 0;
        if (isSelfMember) {
            BusBus._sendone(
                channel,
                "mail.record/insert",
                new mailDataHelpers.Store(this.browse(channel.id), {
                    invited_member_ids: kwargs.invite_to_rtc_call
                        ? [["ADD", insertedChannelMembers]]
                        : false,
                    member_count: DiscussChannelMember.search_count([
                        ["channel_id", "=", channel.id],
                    ]),
                })
                    .add(DiscussChannelMember.browse(insertedChannelMembers))
                    .get_result()
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
    _create_channel(name, group_id) {
        const kwargs = getKwArgs(arguments, "name", "group_id");
        name = kwargs.name;
        group_id = kwargs.group_id;

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const id = this.create({
            channel_member_ids: [Command.create({ partner_id: this.env.user.partner_id })],
            channel_type: "channel",
            name,
            group_public_id: group_id,
        });
        this.write([id], { group_public_id: group_id });
        this.message_post(
            id,
            makeKwArgs({
                body: `<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="${id}">#${name}</a></div>`,
                message_type: "notification",
            })
        );
        const [partner] = ResPartner.read(this.env.user.partner_id);
        this._broadcast([id], [partner]);
        return DiscussChannel.browse(id);
    }

    _channel_basic_info_fields() {
        return [
            "avatar_cache_key",
            "channel_type",
            "create_uid",
            "default_display_mode",
            "description",
            "group_public_id",
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

    /** @param {number[]} ids */
    channel_fetched(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const channels = this.browse(ids);
        for (const channel of channels) {
            if (!["chat", "whatsapp"].includes(channel.channel_type)) {
                continue;
            }
            const channelMessages = MailMessage._filter([
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channel.id],
            ]);
            const lastMessage = channelMessages.reduce((lastMessage, message) => {
                if (message.id > lastMessage.id) {
                    return message;
                }
                return lastMessage;
            }, channelMessages[0]);
            if (!lastMessage) {
                continue;
            }
            const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
            DiscussChannelMember.write([memberOfCurrentUser.id], {
                fetched_message_id: lastMessage.id,
            });
            BusBus._sendone(channel, "discuss.channel.member/fetched", {
                channel_id: channel.id,
                id: memberOfCurrentUser.id,
                last_message_id: lastMessage.id,
                partner_id: this.env.user.partner_id,
            });
        }
    }

    /**
     * @param {number[]} partners_to
     * @param {boolean} [pin=true]
     */
    _get_or_create_chat(partners_to, pin) {
        const kwargs = getKwArgs(arguments, "partners_to", "pin");
        partners_to = kwargs.partners_to || [];
        pin = kwargs.pin ?? true;

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
            partners.map(({ id }) => id)
        );
        return DiscussChannel.browse(id);
    }

    /** @param {number[]} ids */
    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        store = kwargs.store;
        fields = kwargs.fields;

        if (fields && Array.isArray(fields) && fields.length) {
            store._add_record_fields(this, fields);
        } else {
            const bus_last_id = this.env["bus.bus"].lastBusNotificationId;
            /** @type {import("mock_models").DiscussChannelMember} */
            const DiscussChannelMember = this.env["discuss.channel.member"];
            /** @type {import("mock_models").DiscussChannelRtcSession} */
            const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];
            /** @type {import("mock_models").MailMessage} */
            const MailMessage = this.env["mail.message"];
            /** @type {import("mock_models").MailNotification} */
            const MailNotification = this.env["mail.notification"];
            /** @type {import("mock_models").ResGroups}*/
            const ResGroups = this.env["res.groups"];

            for (const channel of this) {
                const members = DiscussChannelMember.browse(channel.channel_member_ids);
                const messages = MailMessage._filter([
                    ["model", "=", "discuss.channel"],
                    ["res_id", "=", channel.id],
                ]);
                const res = this._channel_basic_info([channel.id]);
                res.fetchChannelInfoState = "fetched";
                res.parent_channel_id = mailDataHelpers.Store.one(
                    this.env["discuss.channel"].browse(channel.parent_channel_id)
                );
                res.from_message_id = mailDataHelpers.Store.one(
                    MailMessage.browse(channel.from_message_id)
                );
                res.group_public_id = mailDataHelpers.Store.one(
                    ResGroups.browse(channel.group_public_id),
                    makeKwArgs({ fields: ["full_name"] })
                );
                if (this.env.user) {
                    const message_needaction_counter = MailNotification._filter([
                        ["res_partner_id", "=", this.env.user.partner_id],
                        ["is_read", "=", false],
                        ["mail_message_id", "in", messages.map((message) => message.id)],
                    ]).length;
                    Object.assign(res, {
                        message_needaction_counter,
                        message_needaction_counter_bus_id: bus_last_id,
                    });
                }
                const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
                if (memberOfCurrentUser) {
                    const message_unread_counter = this.env[
                        "discuss.channel.member"
                    ]._compute_message_unread_counter([memberOfCurrentUser.id]);
                    DiscussChannelMember.write([memberOfCurrentUser.id], {
                        message_unread_counter,
                    });
                    store.add(
                        DiscussChannelMember.browse(memberOfCurrentUser.id),
                        makeKwArgs({
                            extra_fields: [
                                "custom_channel_name",
                                "last_interest_dt",
                                "message_unread_counter",
                                mailDataHelpers.Store.one("rtc_inviting_session_id"),
                                "unpin_dt",
                            ],
                        })
                    );
                }
                if (channel.channel_type !== "channel") {
                    const otherMembers = members.filter(
                        (member) => member.id !== memberOfCurrentUser?.id
                    );
                    store.add(otherMembers);
                }
                if (this._member_based_naming_channel_types().includes(channel.channel_type)) {
                    res.channel_name_member_ids = mailDataHelpers.Store.many(
                        this.env["discuss.channel.member"].browse(channel.channel_name_member_ids)
                    );
                }
                res.rtc_session_ids = mailDataHelpers.Store.many(
                    DiscussChannelRtcSession.browse(channel.rtc_session_ids),
                    makeKwArgs({ extra: true, mode: "ADD" })
                );
                store._add_record_fields(this.browse(channel.id), res);
            }
        }
    }

    _member_based_naming_channel_types() {
        return ["group"];
    }

    /**
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     */
    channel_pin(ids, pinned) {
        const kwargs = getKwArgs(arguments, "ids", "pinned");
        ids = kwargs.ids;
        delete kwargs.ids;
        pinned = kwargs.pinned ?? false;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [channel] = this.browse(ids);
        const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
        if (memberOfCurrentUser && memberOfCurrentUser.is_pinned !== pinned) {
            DiscussChannelMember.write([memberOfCurrentUser.id], {
                unpin_dt: pinned ? false : serializeDateTime(today()),
            });
        }
        const [partner] = ResPartner.read(this.env.user.partner_id);
        if (!pinned) {
            BusBus._sendone(
                partner,
                "mail.record/insert",
                new mailDataHelpers.Store(DiscussChannel.browse(channel.id), {
                    close_chat_window: true,
                    id: channel.id,
                }).get_result()
            );
        } else {
            BusBus._sendone(
                partner,
                "mail.record/insert",
                new mailDataHelpers.Store(DiscussChannel.browse(channel.id)).get_result()
            );
        }
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
    channel_set_custom_name(ids, name) {
        const kwargs = getKwArgs(arguments, "ids", "name");
        ids = kwargs.ids;
        delete kwargs.ids;
        name = kwargs.name || "";

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const channelId = ids[0]; // simulate ensure_one.
        const [memberIdOfCurrentUser] = DiscussChannelMember.search([
            ["partner_id", "=", this.env.user.partner_id],
            ["channel_id", "=", channelId],
        ]);
        DiscussChannelMember.write([memberIdOfCurrentUser], {
            custom_channel_name: name,
        });
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(
            partner,
            "mail.record/insert",
            new mailDataHelpers.Store(DiscussChannelMember.browse(memberIdOfCurrentUser), {
                custom_channel_name: name,
            }).get_result()
        );
    }

    /**
     * @param {number[]} partners_to
     * @param {string} name
     * */
    _create_group(partners_to, name) {
        const kwargs = getKwArgs(arguments, "partners_to", "name");
        partners_to = kwargs.partners_to || [];
        name = kwargs.name || "";

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const partners = ResPartner.browse(partners_to);
        const id = this.create({
            channel_type: "group",
            channel_member_ids: partners.map((partner) =>
                Command.create({ partner_id: partner.id })
            ),
            name,
        });
        this._broadcast(
            [id],
            partners.map((partner) => partner.id)
        );
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
        /** @type {import {"mock_model"}.ResPartner} */
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
        const store = new mailDataHelpers.Store(subChannels);
        BusBus._sendone(partner, "mail.record/insert", store.get_result());
        this.message_post(
            self.id,
            makeKwArgs({
                body: `${partner.display_name} started a thread: <a href='#' class='o_channel_redirect' data-oe-id='${subChannels[0].id}' data-oe-model='discuss.channel'>${subChannels[0].name}</a>.`,
                message_type: "notification",
                subtype_xmlid: "mail.mt_comment",
            })
        );
        return {
            store_data: store.get_result(),
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
                channel.channel_type === "channel" ? "channel" : "a private conversation with"
            }
            <b>${
                channel.channel_type === "channel"
                    ? `#${channel.name}`
                    : channel.channel_member_ids.map(
                          (id) => DiscussChannelMember.search_read([["id", "=", id]])[0].name
                      )
            }</b>.<br><br>

            Type <b>@username</b> to mention someone, and grab their attention.<br>
            Type <b>#channel</b> to mention a channel.<br>
            Type <b>/command</b> to execute a command.<br></span>
        `;
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "discuss.channel/transient_message", {
            body: notifBody,
            channel_id: channel.id,
        });
        return true;
    }

    /** @param {number[]} ids */
    execute_command_leave(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        const [channel] = this.browse(ids);
        if (channel.channel_type === "channel") {
            this.action_unfollow([channel.id]);
        } else {
            this.channel_pin([channel.id], false);
        }
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

    /**
     * @param {string} search
     * @param {limit} number
     */
    get_mention_suggestions(search, limit) {
        const kwargs = getKwArgs(arguments, "search", "limit");
        search = kwargs.search || "";
        limit = kwargs.limit || 8;

        /**
         * Returns the given list of channels after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {this[]} channels
         * @param {string} search
         * @param {number} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = (channels, search, limit) => {
            const matchingChannels = channels.filter((channel) => {
                // no search term is considered as return all
                if (!search) {
                    return true;
                }
                // otherwise name or email must match search term
                if (channel.name && channel.name.includes(search)) {
                    return true;
                }
                return false;
            });
            matchingChannels.length = Math.min(matchingChannels.length, limit);
            return matchingChannels;
        };
        const mentionSuggestions = mentionSuggestionsFilter(this, search, limit);
        const store = new mailDataHelpers.Store(
            mentionSuggestions,
            makeKwArgs({
                fields: [
                    "name",
                    "channel_type",
                    "group_public_id",
                    mailDataHelpers.Store.one("parent_channel_id"),
                ],
            })
        );
        return store.get_result();
    }

    /**
     * @param {number[]} ids
     * @param {number[]} known_member_ids
     */
    _load_more_members(ids, known_member_ids) {
        const kwargs = getKwArgs(arguments, "ids", "known_member_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        known_member_ids = kwargs.known_member_ids || [];

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const members = DiscussChannelMember.search(
            [
                ["id", "not in", known_member_ids],
                ["channel_id", "in", ids],
            ],
            makeKwArgs({ limit: 100 })
        );
        const member_count = DiscussChannelMember.search_count([["channel_id", "in", ids]]);
        return new mailDataHelpers.Store(this.browse(ids[0]), { member_count })
            .add(DiscussChannelMember.browse(members))
            .get_result();
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

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const pinned_at = pinned && serializeDateTime(DateTime.now());
        MailMessage.write([message_id], { pinned_at });
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
        const [channel] = this.read(id);
        BusBus._sendone(
            channel,
            "mail.record/insert",
            new mailDataHelpers.Store(MailMessage.browse(message_id), { pinned_at }).get_result()
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
                    new mailDataHelpers.Store(
                        this.browse(channel.id),
                        Object.fromEntries(changes)
                    ).get_result(),
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
     * @param {number[]} partner_ids
     */
    _broadcast(ids, partner_ids) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const notifications = this._channel_channel_notifications(ids, partner_ids);
        BusBus._sendmany(notifications);
    }

    /**
     * @param {number} id
     * @param {number[]} partner_ids
     */
    _channel_channel_notifications(ids, partner_ids) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids;

        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const notifications = [];
        for (const partner_id of partner_ids) {
            const user = ResUsers._filter([["partner_id", "in", partner_id]])[0];
            if (!user) {
                continue;
            }
            // Note: `_to_store` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const [relatedPartner] = ResPartner.search_read([["id", "=", partner_id]]);
            for (const channelId of ids) {
                notifications.push([
                    relatedPartner,
                    "mail.record/insert",
                    new mailDataHelpers.Store(DiscussChannel.browse(channelId)).get_result(),
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
        const channels = this._filter([
            ["channel_type", "in", ["channel", "group"]],
            ["channel_member_ids", "in", members.map((member) => member.id)],
        ]);
        const pinnedChannels = this._filter([
            ["channel_type", "not in", ["channel", "group"]],
            ["channel_member_ids", "in", pinnedMembers.map((member) => member.id)],
        ]);
        return channels.concat(pinnedChannels);
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
