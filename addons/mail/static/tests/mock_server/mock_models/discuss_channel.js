import { assignDefined } from "@mail/utils/common/misc";
import { Command, fields, models, serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";
import { DEFAULT_MAIL_SEARCH_ID, DEFAULT_MAIL_VIEW_ID } from "./constants";
import { parseModelParams } from "../mail_mock_server";
import { Kwargs } from "@web/../tests/_framework/mock_server/mock_server_utils";

const { DateTime } = luxon;

export class DiscussChannel extends models.ServerModel {
    _name = "discuss.channel";
    _inherit = ["mail.thread"];

    _views = {
        [`search,${DEFAULT_MAIL_SEARCH_ID}`]: `<search/>`,
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: `<form/>`,
    };

    author_id = fields.Many2one({
        relation: "res.partner",
        default: () => serverState.partnerId,
    });
    avatarCacheKey = fields.Char({ string: "Avatar Cache Key" });
    channel_member_ids = fields.One2many({
        relation: "discuss.channel.member",
        relation_field: "channel_id",
        string: "Members",
        default: () => [Command.create({ partner_id: serverState.partnerId })],
    });
    channel_type = fields.Generic({ default: "channel" });
    group_public_id = fields.Generic({
        default: () => serverState.groupId,
    });
    uuid = fields.Generic({
        default: () => uniqueId("discuss.channel_uuid-"),
    });
    last_interest_dt = fields.Datetime({ string: "Last Interest" });

    /** @param {number[]} ids */
    action_unfollow(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const channel = this._filter([["id", "in", ids]])[0];
        const [channelMember] = DiscussChannelMember._filter([
            ["channel_id", "in", ids],
            ["partner_id", "=", this.env.user.partner_id],
        ]);
        if (!channelMember) {
            return true;
        }
        this.write([channel.id], {
            channel_member_ids: [Command.delete(channelMember.id)],
        });
        this.message_post(
            channel.id,
            Kwargs({
                author_id: serverState.partnerId,
                body: '<div class="o_mail_notification">left the channel</div>',
                subtype_xmlid: "mail.mt_comment",
            })
        );
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "discuss.channel/leave", { id: channel.id });
        BusBus._sendone(channel, "mail.record/insert", {
            Thread: {
                id: channel.id,
                channelMembers: [["DELETE", { id: channelMember.id }]],
                memberCount: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
                model: "discuss.channel",
            },
        });
        return true;
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partner_ids
     */
    add_members(ids, partner_ids) {
        const kwargs = parseModelParams(arguments, "ids", "partner_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [channel] = this._filter([["id", "in", ids]]);
        const partners = ResPartner._filter([["id", "in", partner_ids]]);
        for (const partner of partners) {
            if (partner.id === this.env.user.partner_id) {
                continue; // adding 'yourself' to the conversation is handled below
            }
            const body = `<div class="o_mail_notification">invited ${partner.name} to the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, Kwargs({ body, message_type, subtype_xmlid }));
        }
        const insertedChannelMembers = [];
        for (const partner of partners) {
            insertedChannelMembers.push(
                DiscussChannelMember.create({
                    channel_id: channel.id,
                    partner_id: partner.id,
                    create_uid: this.env.uid,
                })
            );
            BusBus._sendone(partner, "discuss.channel/joined", {
                channel: { ...this.channel_basic_info([channel.id]), is_pinned: true },
                invited_by_user_id: this.env.uid,
            });
        }
        const selfPartner = partners.find((partner) => partner.id === this.env.user.parter_id);
        if (selfPartner) {
            // needs to be done after adding 'self' as a member
            const body = `<div class="o_mail_notification">${selfPartner.name} joined the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, Kwargs({ body, message_type, subtype_xmlid }));
        }
        const isSelfMember =
            DiscussChannelMember.search_count([
                ["partner_id", "=", this.env.user.partner_id],
                ["channel_id", "=", channel.id],
            ]) > 0;
        if (isSelfMember) {
            BusBus._sendone(channel, "mail.record/insert", {
                Thread: {
                    id: channel.id,
                    channelMembers: [
                        [
                            "ADD",
                            DiscussChannelMember._discuss_channel_member_format(
                                insertedChannelMembers
                            ),
                        ],
                    ],
                    memberCount: DiscussChannelMember.search_count([
                        ["channel_id", "=", channel.id],
                    ]),
                    model: "discuss.channel",
                },
            });
        }
    }

    /**
     * @param {number[]} ids
     * @param {string} description
     */
    channel_change_description(ids, description) {
        const kwargs = parseModelParams(arguments, "ids", "description");
        ids = kwargs.ids;
        delete kwargs.ids;
        description = kwargs.description || "";

        const channel = this._filter([["id", "in", ids]])[0];
        this.write([channel.id], { description });
    }

    /**
     * @param {string} name
     * @param {string} [group_id]
     */
    channel_create(name, group_id) {
        const kwargs = parseModelParams(arguments, "name", "group_id");
        name = kwargs.name;
        group_id = kwargs.group_id;

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
            Kwargs({
                body: `<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="${id}">#${name}</a></div>`,
                message_type: "notification",
            })
        );
        const [partner] = ResPartner.read(this.env.user.partner_id);
        this._broadcast(id, [partner]);
        return this._channel_info([id])[0];
    }

    /** @param {number[]} ids */
    channel_basic_info(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResGroups} */
        const ResGroups = this.env["res.groups"];

        const [channel] = this._filter([["id", "in", ids]]);
        const res = assignDefined({}, channel, [
            "allow_public_upload",
            "avatarCacheKey", // mock server simplification
            "channel_type",
            "create_uid",
            "description",
            "id",
            "last_interest_dt",
            "name",
            "uuid",
        ]);
        const [group_public_id] = ResGroups._filter([["id", "=", channel.group_public_id]]);
        const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
        Object.assign(res, {
            authorizedGroupFullName: group_public_id ? group_public_id.name : false,
            defaultDisplayMode: channel.default_display_mode,
            group_based_subscription: channel.group_ids.length > 0,
            is_editable: (() => {
                switch (channel.channel_type) {
                    case "channel":
                        return channel.create_uid === this.env.uid;
                    case "group":
                        return memberOfCurrentUser;
                    default:
                        return false;
                }
            })(),
            memberCount: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
            model: "discuss.channel",
        });
        return res;
    }

    /** @param {number[]} ids */
    channel_fetched(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const channels = this._filter([["id", "in", ids]]);
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

    /** @param {number[]} ids */
    channel_fetch_preview(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const channels = this._filter([["id", "in", ids]]);
        return channels
            .map((channel) => {
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
                return {
                    id: channel.id,
                    last_message: lastMessage
                        ? MailMessage.message_format([lastMessage.id])[0]
                        : false,
                };
            })
            .filter((preview) => preview.last_message);
    }

    /**
     * @param {number[]} partners_to
     * @param {boolean} [pin=true]
     */
    channel_get(partners_to, pin) {
        const kwargs = parseModelParams(arguments, "partners_to", "pin");
        partners_to = kwargs.partners_to || [];
        pin = kwargs.pin ?? true;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (partners_to.length === 0) {
            return false;
        }
        if (!partners_to.includes(this.env.user.partner_id)) {
            partners_to.push(this.env.user.partner_id);
        }
        const partners = ResPartner._filter([["id", "in", partners_to]], { active_test: false });
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
                return this._channel_info([channel.id])[0];
            }
        }
        const id = this.create({
            channel_member_ids: partners.map((partner) =>
                Command.create({ partner_id: partner.id })
            ),
            channel_type: "chat",
            name: partners.map((partner) => partner.name).join(", "),
        });
        this._broadcast(
            id,
            partners.map(({ id }) => id)
        );
        return this._channel_info([id])[0];
    }

    /** @param {number[]} ids */
    _channel_info(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").DiscussChannelRtcSession} */
        const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        const channels = this._filter([["id", "in", ids]]);
        return channels.map((channel) => {
            const members = DiscussChannelMember._filter([
                ["id", "in", channel.channel_member_ids],
            ]);
            const messages = MailMessage._filter([
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channel.id],
            ]);
            const message_needaction_counter = MailNotification._filter([
                ["res_partner_id", "=", this.env.user.partner_id],
                ["is_read", "=", false],
                ["mail_message_id", "in", messages.map((message) => message.id)],
            ]).length;
            const res = this.channel_basic_info([channel.id]);
            Object.assign(res, {
                fetchChannelInfoState: "fetched",
                message_needaction_counter,
            });
            const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
            if (memberOfCurrentUser) {
                Object.assign(res, {
                    is_pinned: memberOfCurrentUser.is_pinned,
                    message_unread_counter: memberOfCurrentUser.message_unread_counter,
                    state: memberOfCurrentUser.fold_state || "closed",
                });
                Object.assign(res, {
                    custom_channel_name: memberOfCurrentUser.custom_channel_name,
                    message_unread_counter: memberOfCurrentUser.message_unread_counter,
                });
                if (memberOfCurrentUser.rtc_inviting_session_id) {
                    res.rtcInvitingSession = {
                        id: memberOfCurrentUser.rtc_inviting_session_id,
                    };
                }
                res.channelMembers = [
                    [
                        "ADD",
                        DiscussChannelMember._discuss_channel_member_format([
                            memberOfCurrentUser.id,
                        ]),
                    ],
                ];
            }
            if (channel.channel_type !== "channel") {
                res.channelMembers = [
                    [
                        "ADD",
                        DiscussChannelMember._discuss_channel_member_format(
                            members.map((member) => member.id)
                        ),
                    ],
                ];
            }
            res.rtcSessions = [
                [
                    "ADD",
                    (channel.rtc_session_ids || []).map((rtcSessionId) =>
                        DiscussChannelRtcSession._mail_rtc_session_format(
                            rtcSessionId,
                            Kwargs({
                                extra: true,
                            })
                        )
                    ),
                ],
            ];
            res.allow_public_upload = channel.allow_public_upload;
            return res;
        });
    }

    /**
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     */
    channel_pin(ids, pinned) {
        const kwargs = parseModelParams(arguments, "ids", "pinned");
        ids = kwargs.ids;
        delete kwargs.ids;
        pinned = kwargs.pinned ?? false;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [channel] = this._filter([["id", "in", ids]]);
        const memberOfCurrentUser = this._find_or_create_member_for_self(channel.id);
        if (memberOfCurrentUser && memberOfCurrentUser.is_pinned !== pinned) {
            DiscussChannelMember.write([memberOfCurrentUser.id], {
                unpin_dt: pinned ? false : serializeDateTime(today())
            });
        }
        const [partner] = ResPartner.read(this.env.user.partner_id);
        if (!pinned) {
            BusBus._sendone(partner, "discuss.channel/unpin", {
                id: channel.id,
            });
        } else {
            BusBus._sendone(partner, "mail.record/insert", {
                Thread: this._channel_info([channel.id])[0],
            });
        }
    }

    /**
     * @param {number[]} ids
     * @param {string} name
     */
    channel_rename(ids, name) {
        const kwargs = parseModelParams(arguments, "ids", "name");
        ids = kwargs.ids;
        delete kwargs.ids;
        name = kwargs.name || "";

        const channel = this._filter([["id", "in", ids]])[0];
        this.write([channel.id], { name });
    }

    /**
     * @param {number[]} ids
     * @param {string} name
     */
    channel_set_custom_name(ids, name) {
        const kwargs = parseModelParams(arguments, "ids", "name");
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
        BusBus._sendone(partner, "mail.record/insert", {
            Thread: {
                custom_channel_name: name,
                id: channelId,
                model: "discuss.channel",
            },
        });
    }

    /** @param {number[]} partners_to */
    create_group(partners_to) {
        const kwargs = parseModelParams(arguments, "partners_to");
        partners_to = kwargs.partners_to || [];

        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const partners = ResPartner._filter([["id", "in", partners_to]], { active_test: false });
        const id = this.create({
            channel_type: "group",
            channel_member_ids: partners.map((partner) =>
                Command.create({ partner_id: partner.id })
            ),
            name: "",
        });
        this._broadcast(
            id,
            partners.map((partner) => partner.id)
        );
        return this._channel_info([id])[0];
    }

    /** @param {number} id */
    execute_command_help(ids) {
        const kwargs = parseModelParams(arguments, "ids");
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
            thread: { model: "discuss.channel", id: channel.id },
        });
        return true;
    }

    /** @param {number[]} ids */
    execute_command_leave(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        const channel = this._filter([["id", "in", ids]])[0];
        if (channel.channel_type === "channel") {
            this.action_unfollow([channel.id]);
        } else {
            this.channel_pin([channel.id], false);
        }
    }

    /** @param {number[]} ids */
    execute_command_who(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const channels = this._filter([["id", "in", ids]]);
        for (const channel of channels) {
            const members = DiscussChannelMember._filter([
                ["id", "in", channel.channel_member_ids],
            ]);
            const otherPartnerIds = members
                .filter(
                    (member) => member.partner_id && member.partner_id !== this.env.user.partner_id
                )
                .map((member) => member.partner_id);
            const otherPartners = ResPartner._filter([["id", "in", otherPartnerIds]]);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners
                    .map((partner) => partner.name)
                    .join(", ")} and you`;
            }
            const [partner] = ResPartner.read(this.env.user.partner_id);
            BusBus._sendone(partner, "discuss.channel/transient_message", {
                body: `<span class="o_mail_notification">${message}</span>`,
                thread: { model: "discuss.channel", id: channel.id },
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
        const kwargs = parseModelParams(arguments, "search", "limit");
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
            const matchingChannels = channels
                .filter((channel) => {
                    // no search term is considered as return all
                    if (!search) {
                        return true;
                    }
                    // otherwise name or email must match search term
                    if (channel.name && channel.name.includes(search)) {
                        return true;
                    }
                    return false;
                })
                .map((channel) => {
                    // expected format
                    return {
                        authorizedGroupFullName: channel.group_public_id
                            ? channel.group_public_id.name
                            : false,
                        channel_type: channel.channel_type,
                        id: channel.id,
                        model: "discuss.channel",
                        name: channel.name,
                    };
                });
            // reduce results to max limit
            matchingChannels.length = Math.min(matchingChannels.length, limit);
            return matchingChannels;
        };
        const mentionSuggestions = mentionSuggestionsFilter(this, search, limit);
        return mentionSuggestions;
    }

    /**
     * @param {number[]} ids
     * @param {number[]} known_member_ids
     */
    load_more_members(ids, known_member_ids) {
        const kwargs = parseModelParams(arguments, "ids", "known_member_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        known_member_ids = kwargs.known_member_ids || [];

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const members = DiscussChannelMember.search_read(
            [
                ["id", "not in", known_member_ids],
                ["channel_id", "in", ids],
            ],
            undefined,
            100
        );
        const memberCount = DiscussChannelMember.search_count([["channel_id", "in", ids]]);
        return {
            channelMembers: [
                [
                    "ADD",
                    DiscussChannelMember._discuss_channel_member_format(members.map((m) => m.id)),
                ],
            ],
            memberCount,
        };
    }

    /** @param {number} id */
    message_post(id) {
        const kwargs = parseModelParams(arguments, "id");
        id = kwargs.id;
        delete kwargs.id;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        kwargs.message_type ||= "notification";
        const channel = this._filter([["id", "=", id]])[0];
        this.write([id], {
            last_interest_dt: serializeDateTime(today()),
        });
        const messageData = MailThread.message_post.call(this, [id], kwargs);
        if (kwargs.author_id === this.env.user?.partner_id) {
            this._set_last_seen_message([channel.id], messageData.id);
        }
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
        return messageData;
    }

    /**
     * @param {number} id
     * @param {number} message_id
     * @param {boolean} pinned
     */
    set_message_pin(id, message_id, pinned) {
        const kwargs = parseModelParams(arguments, "id", "message_id", "pinned");
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
            Kwargs({
                body: notification,
                message_type: "notification",
                subtype_xmlid: "mail.mt_comment",
            })
        );
        const [channel] = this.read(id);
        BusBus._sendone(channel, "mail.record/insert", {
            Message: {
                id: message_id,
                pinned_at,
            },
        });
    }

    /** @type {typeof models.Model["prototype"]["write"]} */
    write(idOrIds, values, kwargs) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const [firstId] = ensureArray(idOrIds);
        if ("image_128" in values) {
            super.write(firstId, {
                avatarCacheKey: DateTime.utc().toFormat("yyyyMMddHHmmss"),
            });
            const channel = this.search_read([["id", "=", firstId]])[0];
            return BusBus._sendone(channel, "mail.record/insert", {
                Thread: {
                    avatarCacheKey: channel.avatarCacheKey,
                    id: firstId,
                    model: "discuss.channel",
                },
            });
        }
        const notifications = [];
        const [channel] = this._filter([["id", "=", firstId]]);
        if (channel) {
            const diff = {};
            for (const key in values) {
                if (channel[key] !== values[key] && key !== "image_128") {
                    diff[key] = values[key];
                }
            }
            notifications.push([
                channel,
                "mail.record/insert",
                {
                    Thread: {
                        id: channel.id,
                        model: "discuss.channel",
                        ...diff,
                    },
                },
            ]);
        }
        const result = super.write(idOrIds, values, kwargs);
        if (notifications.length) {
            BusBus._sendmany(notifications);
        }
        return result;
    }

    /**
     * @param {number} id
     * @param {number[]} partner_ids
     */
    _broadcast(ids, partner_ids) {
        const kwargs = parseModelParams(arguments, "ids", "partner_ids");
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
        const kwargs = parseModelParams(arguments, "ids", "partner_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids;

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
            // Note: `_channel_info` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const channelInfos = this._channel_info(ids);
            const [relatedPartner] = ResPartner.search_read([["id", "=", partner_id]]);
            for (const channelInfo of channelInfos) {
                notifications.push([relatedPartner, "mail.record/insert", { Thread: channelInfo }]);
            }
        }
        return notifications;
    }

    /**
     * @param {number[]} ids
     * @param {number} last_message_id
     */
    _channel_seen(ids, last_message_id) {
        const kwargs = parseModelParams(arguments, "ids", "last_message_id");
        ids = kwargs.ids;
        delete kwargs.ids;
        last_message_id = kwargs.last_message_id;

        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        // Update record
        const channel_id = ids[0];
        if (!channel_id) {
            throw new Error("Should only be one channel in channel_seen mock params");
        }
        const [channel] = this._filter([["id", "=", channel_id]]);
        const messages = MailMessage._filter([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channel.id],
        ]);
        if (!messages || messages.length === 0 || !channel) {
            return;
        }
        this._set_last_seen_message([channel.id], last_message_id);
    }

    /**
     * @param {number[]} ids
     * @param {number} message_id
     */
    _set_last_seen_message(ids, message_id) {
        const kwargs = parseModelParams(arguments, "ids", "message_id");
        ids = kwargs.ids;
        delete kwargs.ids;
        message_id = kwargs.message_id;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const memberOfCurrentUser = this._find_or_create_member_for_self(ids[0]);
        if (memberOfCurrentUser) {
            DiscussChannelMember.write([memberOfCurrentUser.id], {
                fetched_message_id: message_id,
                seen_message_id: message_id,
            });
        }
        const [channel] = this.search_read([["id", "in", ids]]);
        const [partner, guest] = ResPartner._get_current_persona();
        let target = guest ?? partner;
        if (this._types_allowing_seen_infos().includes(channel.channel_type)) {
            target = channel;
        }
        BusBus._sendone(target, "discuss.channel.member/seen", {
            channel_id: channel.id,
            id: memberOfCurrentUser?.id,
            last_message_id: message_id,
            [guest ? "guest_id" : "partner_id"]: guest?.id ?? partner?.id,
        });
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

    /** @param {number} id */
    _find_or_create_member_for_self(id) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [partner, guest] = ResPartner._get_current_persona();
        if (!partner && !guest) {
            return;
        }
        return DiscussChannelMember.search_read([
            ["channel_id", "=", id],
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", partner.id],
        ])[0];
    }

    _find_or_create_persona_for_channel(id, guest_name) {
        const kwargs = parseModelParams(arguments, "id", "guest_name");
        id = kwargs.id;
        delete kwargs.id;
        guest_name = kwargs.guest_name;

        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        if (DiscussChannel._find_or_create_member_for_self(id)) {
            return;
        }
        const guestId =
            MailGuest._get_guest_from_context()?.id ?? MailGuest.create({ name: guest_name });
        DiscussChannel.write([id], {
            channel_member_ids: [Command.create({ guest_id: guestId })],
        });
        MailGuest._set_auth_cookie(guestId);
    }
}
