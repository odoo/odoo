/** @odoo-module */

import { assignDefined } from "@mail/utils/common/misc";
import { Command, constants, fields, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

const { DateTime } = luxon;

export class DiscussChannel extends models.ServerModel {
    _name = "discuss.channel";
    _inherit = ["mail.thread"];

    author_id = fields.Many2one({
        relation: "res.partner",
        default: () => constants.PARTNER_ID,
    });
    avatarCacheKey = fields.Datetime({ string: "Avatar Cache Key" });
    channel_member_ids = fields.One2many({
        relation: "discuss.channel.member",
        relation_field: "channel_id",
        string: "Members",
        default: () => [Command.create({ partner_id: constants.PARTNER_ID })],
    });
    channel_type = fields.Generic({ default: "channel" });
    group_based_subscription = fields.Boolean();
    group_public_id = fields.Generic({
        default: () => constants.GROUP_ID,
    });
    uuid = fields.Generic({
        default: () => uniqueId("discuss.channel_uuid-"),
    });

    /**
     * @param {number[]} ids
     * @param {KwArgs} [kwargs]
     */
    action_unfollow(ids, kwargs = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const channel = this._filter([["id", "in", ids]])[0];
        const [channelMember] = DiscussChannelMember._filter([
            ["channel_id", "in", ids],
            ["partner_id", "=", constants.PARTNER_ID],
        ]);
        if (!channelMember) {
            return true;
        }
        this.write([channel.id], {
            channel_member_ids: [Command.delete(channelMember.id)],
        });
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        BusBus._sendone(partner, "discuss.channel/leave", { id: channel.id });
        BusBus._sendone(channel, "mail.record/insert", {
            Thread: {
                id: channel.id,
                channelMembers: [["DELETE", { id: channelMember.id }]],
                memberCount: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
                model: "discuss.channel",
            },
        });

        /**
         * Leave message not posted here because it would send the new message
         * notification on a separate bus notification list from the unsubscribe
         * itself which would lead to the channel being pinned again (handler
         * for unsubscribe is weak and is relying on both of them to be sent
         * together on the bus).
         */
        // this.message_post(channel.id, {
        //     author_id: constants.PARTNER_ID,
        //     body: '<div class="o_mail_notification">left the channel</div>',
        //     subtype_xmlid: "mail.mt_comment",
        // });
        return true;
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partnerIds
     * @param {KwArgs<{ partner_ids: number[] }>} [kwargs]
     */
    add_members(ids, partnerIds, kwargs = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        partnerIds = kwargs.partner_ids || partnerIds || [];
        const [channel] = this._filter([["id", "in", ids]]);
        const partners = ResPartner._filter([["id", "in", partnerIds]]);
        for (const partner of partners) {
            if (partner.id === constants.PARTNER_ID) {
                continue; // adding 'yourself' to the conversation is handled below
            }
            const body = `<div class="o_mail_notification">invited ${partner.name} to the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, { body, message_type, subtype_xmlid });
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
                channel: this.channel_info([channel.id])[0],
                invited_by_user_id: this.env.uid,
            });
        }
        const selfPartner = partners.find((partner) => partner.id === constants.PARTNER_ID);
        if (selfPartner) {
            // needs to be done after adding 'self' as a member
            const body = `<div class="o_mail_notification">${selfPartner.name} joined the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, { body, message_type, subtype_xmlid });
        }
        const isSelfMember =
            DiscussChannelMember.search_count([
                ["partner_id", "=", constants.PARTNER_ID],
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
     * @param {KwArgs<{ description: string }>} [kwargs]
     */
    channel_change_description(ids, description, kwargs = {}) {
        description = kwargs.description || description || "";
        const channel = this._filter([["id", "in", ids]])[0];
        this.write([channel.id], { description });
    }

    /**
     * @param {string} name
     * @param {string} [group_id]
     */
    channel_create(name, group_id) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const id = this.create({
            channel_member_ids: [Command.create({ partner_id: constants.PARTNER_ID })],
            channel_type: "channel",
            name,
            group_public_id: group_id,
        });
        this.write([id], {
            group_public_id: group_id,
        });
        this.message_post(id, {
            body: `<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="${id}">#${name}</a></div>`,
            message_type: "notification",
        });
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        this._broadcast(id, [partner]);
        return this.channel_info([id])[0];
    }

    /** @param {number[]} ids */
    channel_fetched(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const channels = this._filter([["id", "in", ids]]);
        for (const channel of channels) {
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
            const memberOfCurrentUser = DiscussChannelMember._getAsSudoFromContext(channel.id);
            DiscussChannelMember.write([memberOfCurrentUser.id], {
                fetched_message_id: lastMessage.id,
            });
            BusBus._sendone(channel, "discuss.channel.member/fetched", {
                channel_id: channel.id,
                id: memberOfCurrentUser.id,
                last_message_id: lastMessage.id,
                partner_id: constants.PARTNER_ID,
            });
        }
    }

    /** @param {number[]} ids */
    channel_fetch_preview(ids) {
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
     * @param {number[]} [partnersTo=[]]
     * @param {boolean} [pin]
     * @param {KwArgs<{ partners_to: number[]; pin: boolean }>} [kwargs]
     */
    channel_get(partnersTo, pin, kwargs = {}) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        partnersTo = kwargs.partners_to || partnersTo || [];
        if (partnersTo.length === 0) {
            return false;
        }
        if (!partnersTo.includes(constants.PARTNER_ID)) {
            partnersTo.push(constants.PARTNER_ID);
        }
        const partners = ResPartner._filter([["id", "in", partnersTo]]);
        const channels = this.search_read([["channel_type", "=", "chat"]]);
        for (const channel of channels) {
            const channelMemberIds = DiscussChannelMember.search([
                ["channel_id", "=", channel.id],
                ["partner_id", "in", partnersTo],
            ]);
            if (
                channelMemberIds.length === partners.length &&
                channel.channel_member_ids.length === partners.length
            ) {
                return this.channel_info([channel.id])[0];
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
        return this.channel_info([id])[0];
    }

    /** @param {number[]} ids */
    channel_info(ids) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").DiscussChannelRtcSession} */
        const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").ResGroups} */
        const ResGroups = this.env["res.groups"];

        const channels = this._filter([["id", "in", ids]]);
        return channels.map((channel) => {
            const members = DiscussChannelMember._filter([
                ["id", "in", channel.channel_member_ids],
            ]);
            const messages = MailMessage._filter([
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channel.id],
            ]);
            const [group_public_id] = ResGroups._filter([["id", "=", channel.group_public_id]]);
            const messageNeedactionCounter = MailNotification._filter([
                ["res_partner_id", "=", constants.PARTNER_ID],
                ["is_read", "=", false],
                ["mail_message_id", "in", messages.map((message) => message.id)],
            ]).length;
            const res = assignDefined({}, channel, [
                "id",
                "name",
                "defaultDisplayMode",
                "description",
                "uuid",
                "create_uid",
                "group_based_subscription",
                "avatarCacheKey",
            ]);
            Object.assign(res, {
                channel_type: channel.channel_type,
                memberCount: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
                message_needaction_counter: messageNeedactionCounter,
                authorizedGroupFullName: group_public_id ? group_public_id.name : false,
                model: "discuss.channel",
            });
            const memberOfCurrentUser = DiscussChannelMember._getAsSudoFromContext(channel.id);
            if (memberOfCurrentUser) {
                Object.assign(res, {
                    is_minimized: memberOfCurrentUser.is_minimized,
                    is_pinned: memberOfCurrentUser.is_pinned,
                    last_interest_dt: memberOfCurrentUser.last_interest_dt,
                    message_unread_counter: memberOfCurrentUser.message_unread_counter,
                    state: memberOfCurrentUser.fold_state || "open",
                    seen_message_id: Array.isArray(memberOfCurrentUser.seen_message_id)
                        ? memberOfCurrentUser.seen_message_id[0]
                        : memberOfCurrentUser.seen_message_id,
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
                res.seenInfos = members
                    .filter((member) => member.partner_id)
                    .map((member) => {
                        return {
                            partner_id: member.partner_id,
                            seen_message_id: member.seen_message_id,
                            fetched_message_id: member.fetched_message_id,
                        };
                    });
                res.channelMembers = [
                    [
                        "ADD",
                        DiscussChannelMember._discuss_channel_member_format(
                            members.map((member) => member.id)
                        ),
                    ],
                ];
            }
            let is_editable;
            switch (channel.channel_type) {
                case "channel":
                    is_editable = channel.create_uid === this.env.uid;
                    break;
                case "group":
                    is_editable = memberOfCurrentUser;
                    break;
                default:
                    is_editable = false;
                    break;
            }
            res.is_editable = is_editable;
            res.rtcSessions = [
                [
                    "ADD",
                    (channel.rtc_session_ids || []).map((rtcSessionId) =>
                        DiscussChannelRtcSession._mailRtcSessionFormat(rtcSessionId, {
                            extra: true,
                        })
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
     * @param {KwArgs<{ pinned: boolean }>} [kwargs]
     */
    channel_pin(ids, pinned, kwargs = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        pinned = kwargs.pinned ?? pinned ?? false;
        const [channel] = this._filter([["id", "in", ids]]);
        const memberOfCurrentUser = DiscussChannelMember._getAsSudoFromContext(channel.id);
        if (memberOfCurrentUser && memberOfCurrentUser.is_pinned !== pinned) {
            DiscussChannelMember.write([memberOfCurrentUser.id], {
                is_pinned: pinned,
            });
        }
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        if (!pinned) {
            BusBus._sendone(partner, "discuss.channel/unpin", {
                id: channel.id,
            });
        } else {
            BusBus._sendone(partner, "mail.record/insert", {
                Thread: this.channel_info([channel.id])[0],
            });
        }
    }

    /**
     * @param {number[]} ids
     * @param {string} name
     * @param {KwArgs<{ name: string }>} [kwargs]
     */
    channel_rename(ids, name, kwargs = {}) {
        name = kwargs.name || name || "";
        const channel = this._filter([["id", "in", ids]])[0];
        this.write([channel.id], { name });
    }

    /**
     * @param {number[]} ids
     * @param {string} name
     * @param {KwArgs<{ name: string }>} [kwargs]
     */
    channel_set_custom_name(ids, name, kwargs = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        name = kwargs.name || name || "";
        const channelId = ids[0]; // simulate ensure_one.
        const [memberIdOfCurrentUser] = DiscussChannelMember.search([
            ["partner_id", "=", constants.PARTNER_ID],
            ["channel_id", "=", channelId],
        ]);
        DiscussChannelMember.write([memberIdOfCurrentUser], {
            custom_channel_name: name,
        });
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        BusBus._sendone(partner, "mail.record/insert", {
            Thread: {
                custom_channel_name: name,
                id: channelId,
                model: "discuss.channel",
            },
        });
    }

    /**
     * @param {number[]} partnersTo
     * @param {KwArgs<{ partners_to: number[] }>} [kwargs]
     */
    create_group(partnersTo, kwargs = {}) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        partnersTo = kwargs.partners_to || partnersTo || [];
        const partners = ResPartner._filter([["id", "in", partnersTo]]);
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
        return this.channel_info([id])[0];
    }

    /** @param {number} id */
    execute_command_help(ids) {
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
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        BusBus._sendone(partner, "discuss.channel/transient_message", {
            body: notifBody,
            thread: { model: "discuss.channel", id: channel.id },
        });
        return true;
    }

    /**
     * @param {number[]} ids
     * @param {KwArgs} kwargs
     */
    execute_command_leave(ids, kwargs = {}) {
        const channel = this._filter([["id", "in", ids]])[0];
        if (channel.channel_type === "channel") {
            this.action_unfollow([channel.id], kwargs);
        } else {
            this.channel_pin([channel.id], false);
        }
    }

    /** @param {number[]} ids */
    execute_command_who(ids) {
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
                .filter((member) => member.partner_id && member.partner_id !== constants.PARTNER_ID)
                .map((member) => member.partner_id);
            const otherPartners = ResPartner._filter([["id", "in", otherPartnerIds]]);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners
                    .map((partner) => partner.name)
                    .join(", ")} and you`;
            }
            const [partner] = ResPartner.read(constants.PARTNER_ID);
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
            : [["partner_id", "=", constants.PARTNER_ID]];
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
     * @param {KwArgs<{ search: string; limit: number }>} [kwargs]
     */
    get_mention_suggestions(search, limit, kwargs = {}) {
        search = kwargs.search || search || "";
        limit = kwargs.limit || limit || 8;

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
     * @param {number[]} channelIds
     * @param {number[]} knownMemberIds
     * @param {KwArgs<{ channel_ids: number[]; known_member_ids: number[] }>} [kwargs]
     */
    load_more_members(channelIds, knownMemberIds, kwargs = {}) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        channelIds = kwargs.channel_ids || channelIds || [];
        knownMemberIds = kwargs.known_member_ids || knownMemberIds || [];
        const members = DiscussChannelMember.search_read(
            [
                ["id", "not in", knownMemberIds],
                ["channel_id", "in", channelIds],
            ],
            { limit: 100 }
        );
        const memberCount = DiscussChannelMember.search_count([["channel_id", "in", channelIds]]);
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

    /**
     * Simulates `message_post` on `discuss.channel`.
     *
     * @param {number} id
     * @param {string} message_type
     * @param {KwArgs<{ message_type: string }>} kwargs
     */
    message_post(id, message_type, kwargs = {}) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        message_type = kwargs.message_type || message_type || "notification";
        const channel = this._filter([["id", "=", id]])[0];
        if (channel.channel_type !== "channel") {
            const memberOfCurrentUser = DiscussChannelMember._getAsSudoFromContext(channel.id);
            if (memberOfCurrentUser) {
                DiscussChannelMember.write([memberOfCurrentUser.id], {
                    last_interest_dt: serializeDateTime(today()),
                    is_pinned: true,
                });
            }
        }
        const messageData = MailThread.message_post([id], {
            ...kwargs,
            message_type,
            model: "discuss.channel",
        });
        if (kwargs.author_id === constants.PARTNER_ID) {
            this._set_last_seen_message([channel.id], messageData.id);
        }
        // simulate compute of message_unread_counter
        const memberOfCurrentUser = DiscussChannelMember._getAsSudoFromContext(channel.id);
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
     * @param {KwArgs<{ message_id: number; pinned: boolean }>} [kwargs]
     */
    set_message_pin(id, { message_id, pinned } = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const pinnedAt = pinned && serializeDateTime(DateTime.now());
        MailMessage.write([message_id], { pinned_at: pinnedAt });
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        const notification = `<div data-oe-type="pin" class="o_mail_notification">
                ${partner.display_name} pinned a
                <a href="#" data-oe-type="highlight" data-oe-id='${message_id}'>message</a> to this channel.
                <a href="#" data-oe-type="pin-menu">See all pinned messages</a>
            </div>`;
        this.message_post(id, {
            body: notification,
            message_type: "notification",
            subtype_xmlid: "mail.mt_comment",
        });
        const [channel] = this.search_read([["id", "=", id]]);
        BusBus._sendone(channel, "mail.record/insert", {
            Message: {
                id: message_id,
                pinned_at: pinnedAt,
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
            // Note: `channel_info` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const channelInfos = this.channel_info(ids);
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
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        // Update record
        const channel_id = ids[0];
        if (!channel_id) {
            throw new Error("Should only be one channel in channel_seen mock params");
        }
        const channel = this._filter([["id", "=", channel_id]])[0];
        const messages = MailMessage._filter([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channel.id],
        ]);
        if (!messages || messages.length === 0) {
            return;
        }
        if (!channel) {
            return;
        }
        this._set_last_seen_message([channel.id], last_message_id);
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        BusBus._sendone(
            channel.channel_type === "chat" ? channel : partner,
            "discuss.channel.member/seen",
            {
                channel_id: channel.id,
                last_message_id: last_message_id,
                partner_id: constants.PARTNER_ID,
            }
        );
    }

    /**
     * @param {number[]} ids
     * @param {number} message_id
     */
    _set_last_seen_message(ids, message_id) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const memberOfCurrentUser = DiscussChannelMember._getAsSudoFromContext(ids[0]);
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
            [guest ? "guest_id" : "partner_id"]: guest?.id ?? partner.id,
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
            : [["partner_id", "=", constants.PARTNER_ID]];
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
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const guest = MailGuest._get_guest_from_context();
        return DiscussChannelMember.search_read([
            ["channel_id", "=", id],
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", constants.PARTNER_ID],
        ])[0];
    }
}
