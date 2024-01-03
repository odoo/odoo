/** @odoo-module */

import { assignDefined } from "@mail/utils/common/misc";
import { Command, fields, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";
import { session } from "@web/session";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

const { DateTime } = luxon;

export class DiscussChannel extends models.ServerModel {
    _name = "discuss.channel";

    author_id = fields.Many2one({
        relation: "res.partner",
        default: () => this.env.partner_id,
    });
    avatarCacheKey = fields.Datetime({ string: "Avatar Cache Key" });
    channel_member_ids = fields.Generic({
        default: () => [Command.create({ partner_id: this.env.partner_id })],
    });
    channel_type = fields.Generic({ default: "channel" });
    group_based_subscription = fields.Boolean();
    group_public_id = fields.Generic({
        default: () => session.group_id,
    });
    uuid = fields.Generic({
        default: () => uniqueId("discuss.channel_uuid-"),
    });

    /**
     * Simulates `action_unfollow` on `discuss.channel`.
     *
     * @param {number[]} ids
     * @param {KwArgs} [kwargs]
     */
    action_unfollow(ids, kwargs = {}) {
        const channel = this._filter([["id", "in", ids]])[0];
        const [channelMember] = this.env["discuss.channel.member"]._filter([
            ["channel_id", "in", ids],
            ["partner_id", "=", this.env.partner_id],
        ]);
        if (!channelMember) {
            return true;
        }
        this.write([channel.id], {
            channel_member_ids: [Command.delete(channelMember.id)],
        });
        this.env["bus.bus"]._sendone(this.env.partner, "discuss.channel/leave", {
            id: channel.id,
        });
        this.env["bus.bus"]._sendone(channel, "mail.record/insert", {
            Thread: {
                id: channel.id,
                channelMembers: [["DELETE", { id: channelMember.id }]],
                memberCount: this.env["discuss.channel.member"].search_count([
                    ["channel_id", "=", channel.id],
                ]),
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
        //     author_id: this.env.partner_id,
        //     body: '<div class="o_mail_notification">left the channel</div>',
        //     subtype_xmlid: "mail.mt_comment",
        // });
        return true;
    }

    /**
     * Simulates `add_members` on `discuss.channel`.
     *
     * @param {number[]} ids
     * @param {number[]} partnerIds
     * @param {KwArgs<{ partner_ids: number[] }>} [kwargs]
     */
    add_members(ids, partnerIds, kwargs = {}) {
        partnerIds = kwargs.partner_ids || partnerIds || [];
        const [channel] = this._filter([["id", "in", ids]]);
        const partners = this.env["res.partner"]._filter([["id", "in", partnerIds]]);
        for (const partner of partners) {
            if (partner.id === this.env.partner_id) {
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
                this.env["discuss.channel.member"].create({
                    channel_id: channel.id,
                    partner_id: partner.id,
                    create_uid: this.env.uid,
                })
            );
            this.env["bus.bus"]._sendone(partner, "discuss.channel/joined", {
                channel: this.channel_info([channel.id])[0],
                invited_by_user_id: this.env.uid,
            });
        }
        const selfPartner = partners.find((partner) => partner.id === this.env.partner_id);
        if (selfPartner) {
            // needs to be done after adding 'self' as a member
            const body = `<div class="o_mail_notification">${selfPartner.name} joined the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this.message_post(channel.id, { body, message_type, subtype_xmlid });
        }
        const isSelfMember =
            this.env["discuss.channel.member"].search_count([
                ["partner_id", "=", this.env.partner_id],
                ["channel_id", "=", channel.id],
            ]) > 0;
        if (isSelfMember) {
            this.env["bus.bus"]._sendone(channel, "mail.record/insert", {
                Thread: {
                    id: channel.id,
                    channelMembers: [
                        [
                            "ADD",
                            this.env["discuss.channel.member"]._discussChannelMemberFormat(
                                insertedChannelMembers
                            ),
                        ],
                    ],
                    memberCount: this.env["discuss.channel.member"].search_count([
                        ["channel_id", "=", channel.id],
                    ]),
                    model: "discuss.channel",
                },
            });
        }
    }

    /**
     * Simulates `channel_change_description` on `discuss.channel`.
     *
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
     * Simulates 'channel_create' on 'discuss.channel'.
     *
     * @param {string} name
     * @param {string} [group_id]
     */
    channel_create(name, group_id) {
        const id = this.create({
            channel_member_ids: [Command.create({ partner_id: this.env.partner_id })],
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
        this._broadcast(id, [this.env.partner]);
        return this.channel_info([id])[0];
    }

    /**
     * Simulates `channel_fetched` on `discuss.channel`.
     *
     * @param {number[]} ids
     */
    channel_fetched(ids) {
        const channels = this._filter([["id", "in", ids]]);
        for (const channel of channels) {
            const channelMessages = this.env["mail.message"]._filter([
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
            const memberOfCurrentUser = this.env["discuss.channel.member"]._getAsSudoFromContext(
                channel.id
            );
            this.env["discuss.channel.member"].write([memberOfCurrentUser.id], {
                fetched_message_id: lastMessage.id,
            });
            this.env["bus.bus"]._sendone(channel, "discuss.channel.member/fetched", {
                channel_id: channel.id,
                id: memberOfCurrentUser.id,
                last_message_id: lastMessage.id,
                partner_id: this.env.partner_id,
            });
        }
    }

    /**
     * Simulates `channel_fetch_preview` on `discuss.channel`.
     *
     * @param {number[]} ids
     */
    channel_fetch_preview(ids) {
        const channels = this._filter([["id", "in", ids]]);
        return channels
            .map((channel) => {
                const channelMessages = this.env["mail.message"]._filter([
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
                        ? this.env["mail.message"].message_format([lastMessage.id])[0]
                        : false,
                };
            })
            .filter((preview) => preview.last_message);
    }

    /**
     * Simulates 'channel_get' on 'discuss.channel'.
     *
     * @param {number[]} [partnersTo=[]]
     * @param {boolean} [pin]
     * @param {KwArgs<{ partners_to: number[]; pin: boolean }>} [kwargs]
     */
    channel_get(partnersTo, pin, kwargs = {}) {
        partnersTo = kwargs.partners_to || partnersTo || [];
        if (partnersTo.length === 0) {
            return false;
        }
        if (!partnersTo.includes(this.env.partner_id)) {
            partnersTo.push(this.env.partner_id);
        }
        const partners = this.env["res.partner"]._filter([["id", "in", partnersTo]]);
        const channels = this.search_read([["channel_type", "=", "chat"]]);
        for (const channel of channels) {
            const channelMemberIds = this.env["discuss.channel.member"].search([
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

    /**
     * Simulates `channel_info` on `discuss.channel`.
     *
     * @param {number[]} ids
     */
    channel_info(ids) {
        const channels = this._filter([["id", "in", ids]]);
        return channels.map((channel) => {
            const members = this.env["discuss.channel.member"]._filter([
                ["id", "in", channel.channel_member_ids],
            ]);
            const messages = this.env["mail.message"]._filter([
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channel.id],
            ]);
            const [group_public_id] = this.env["res.groups"]._filter([
                ["id", "=", channel.group_public_id],
            ]);
            const messageNeedactionCounter = this.env["mail.notification"]._filter([
                ["res_partner_id", "=", this.env.partner_id],
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
                memberCount: this.env["discuss.channel.member"].search_count([
                    ["channel_id", "=", channel.id],
                ]),
                message_needaction_counter: messageNeedactionCounter,
                authorizedGroupFullName: group_public_id ? group_public_id.name : false,
                model: "discuss.channel",
            });
            const memberOfCurrentUser = this.env["discuss.channel.member"]._getAsSudoFromContext(
                channel.id
            );
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
                        this.env["discuss.channel.member"]._discussChannelMemberFormat([
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
                        this.env["discuss.channel.member"]._discussChannelMemberFormat(
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
                        this._mailRtcSessionFormat(rtcSessionId, { extra: true })
                    ),
                ],
            ];
            res.allow_public_upload = channel.allow_public_upload;
            return res;
        });
    }

    /**
     * Simulates the `channel_pin` method of `discuss.channel`.
     *
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     * @param {KwArgs<{ pinned: boolean }>} [kwargs]
     */
    channel_pin(ids, pinned, kwargs = {}) {
        pinned = kwargs.pinned ?? pinned ?? false;
        const [channel] = this._filter([["id", "in", ids]]);
        const memberOfCurrentUser = this.env["discuss.channel.member"]._getAsSudoFromContext(
            channel.id
        );
        if (memberOfCurrentUser && memberOfCurrentUser.is_pinned !== pinned) {
            this.env["discuss.channel.member"].write([memberOfCurrentUser.id], {
                is_pinned: pinned,
            });
        }
        if (!pinned) {
            this.env["bus.bus"]._sendone(this.env.partner, "discuss.channel/unpin", {
                id: channel.id,
            });
        } else {
            this.env["bus.bus"]._sendone(this.env.partner, "mail.record/insert", {
                Thread: this.channel_info([channel.id])[0],
            });
        }
    }

    /**
     * Simulates `channel_rename` on `discuss.channel`.
     *
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
     * Simulates `channel_set_custom_name` on `discuss.channel`.
     *
     * @param {number[]} ids
     * @param {string} name
     * @param {KwArgs<{ name: string }>} [kwargs]
     */
    channel_set_custom_name(ids, name, kwargs = {}) {
        name = kwargs.name || name || "";
        const channelId = ids[0]; // simulate ensure_one.
        const [memberIdOfCurrentUser] = this.env["discuss.channel.member"].search([
            ["partner_id", "=", this.env.partner_id],
            ["channel_id", "=", channelId],
        ]);
        this.env["discuss.channel.member"].write([memberIdOfCurrentUser], {
            custom_channel_name: name,
        });
        this.env["bus.bus"]._sendone(this.env.partner, "mail.record/insert", {
            Thread: {
                custom_channel_name: name,
                id: channelId,
                model: "discuss.channel",
            },
        });
    }

    /**
     * Simulates the `create_group` on `discuss.channel`.
     *
     * @param {number[]} partnersTo
     * @param {KwArgs<{ partners_to: number[] }>} [kwargs]
     */
    create_group(partnersTo, kwargs = {}) {
        partnersTo = kwargs.partners_to || partnersTo || [];
        const partners = this.env["res.partner"]._filter([["id", "in", partnersTo]]);
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

    /**
     * Simulates `execute_command_help` on `discuss.channel`.
     *
     * @param {number} id
     */
    execute_command_help(ids) {
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
                          (id) =>
                              this.env["discuss.channel.member"].search_read([["id", "=", id]])[0]
                                  .name
                      )
            }</b>.<br><br>

            Type <b>@username</b> to mention someone, and grab their attention.<br>
            Type <b>#channel</b> to mention a channel.<br>
            Type <b>/command</b> to execute a command.<br></span>
        `;
        this.env["bus.bus"]._sendone(this.env.partner, "discuss.channel/transient_message", {
            body: notifBody,
            originThread: { model: "discuss.channel", id: channel.id },
        });
        return true;
    }

    /**
     * Simulates `execute_command_leave` on `discuss.channel`.
     *
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

    /**
     * Simulates `execute_command_who` on `discuss.channel`.
     *
     * @param {number[]} ids
     */
    execute_command_who(ids) {
        const channels = this._filter([["id", "in", ids]]);
        for (const channel of channels) {
            const members = this.env["discuss.channel.member"]._filter([
                ["id", "in", channel.channel_member_ids],
            ]);
            const otherPartnerIds = members
                .filter((member) => member.partner_id && member.partner_id !== this.env.partner_id)
                .map((member) => member.partner_id);
            const otherPartners = this.env["res.partner"]._filter([["id", "in", otherPartnerIds]]);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners
                    .map((partner) => partner.name)
                    .join(", ")} and you`;
            }
            this.env["bus.bus"]._sendone(this.env.partner, "discuss.channel/transient_message", {
                body: `<span class="o_mail_notification">${message}</span>`,
                originThread: { model: "discuss.channel", id: channel.id },
            });
        }
    }

    /**
     * Simulates the `get_channels_as_member` method on `discuss.channel`.
     */
    get_channels_as_member() {
        const guest = this.env["mail.guest"]._getGuestFromContext();
        const memberDomain = guest
            ? [["guest_id", "=", guest.id]]
            : [["partner_id", "=", this.env.partner_id]];
        const members = this.env["discuss.channel.member"]._filter(memberDomain);
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
     * Simulates `get_mention_suggestions` on `discuss.channel`.
     *
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
         * @param {models.Model} channels
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
     * Simulates `load_more_members` on `discuss.channel`.
     *
     * @param {number[]} channelIds
     * @param {number[]} knownMemberIds
     * @param {KwArgs<{ channel_ids: number[]; known_member_ids: number[] }>} [kwargs]
     */
    load_more_members(channelIds, knownMemberIds, kwargs = {}) {
        channelIds = kwargs.channel_ids || channelIds || [];
        knownMemberIds = kwargs.known_member_ids || knownMemberIds || [];
        const members = this.env["discuss.channel.member"].search_read(
            [
                ["id", "not in", knownMemberIds],
                ["channel_id", "in", channelIds],
            ],
            { limit: 100 }
        );
        const memberCount = this.env["discuss.channel.member"].search_count([
            ["channel_id", "in", channelIds],
        ]);
        return {
            channelMembers: [
                [
                    "ADD",
                    this.env["discuss.channel.member"]._discussChannelMemberFormat(
                        members.map((m) => m.id)
                    ),
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
        message_type = kwargs.message_type || message_type || "notification";
        const channel = this._filter([["id", "=", id]])[0];
        if (channel.channel_type !== "channel") {
            const memberOfCurrentUser = this.env["discuss.channel.member"]._getAsSudoFromContext(
                channel.id
            );
            if (memberOfCurrentUser) {
                this.env["discuss.channel.member"].write([memberOfCurrentUser.id], {
                    last_interest_dt: serializeDateTime(today()),
                    is_pinned: true,
                });
            }
        }
        const messageData = this.env["mail.thread"].message_post([id], {
            ...kwargs,
            message_type,
            model: "discuss.channel",
        });
        if (kwargs.author_id === this.env.partner_id) {
            this._setLastSeenMessage([channel.id], messageData.id);
        }
        // simulate compute of message_unread_counter
        const memberOfCurrentUser = this.env["discuss.channel.member"]._getAsSudoFromContext(
            channel.id
        );
        const otherMembers = this.env["discuss.channel.member"]._filter([
            ["channel_id", "=", channel.id],
            ["id", "!=", memberOfCurrentUser?.id || false],
        ]);
        for (const member of otherMembers) {
            this.env["discuss.channel.member"].write([member.id], {
                message_unread_counter: member.message_unread_counter + 1,
            });
        }
        return messageData;
    }

    /**
     * Simulates `set_message_pin` on `discuss.channel`.
     *
     * @param {number} id
     * @param {KwArgs<{ message_id: number; pinned: boolean }>} [kwargs]
     */
    set_message_pin(id, { message_id, pinned } = {}) {
        const pinnedAt = pinned && serializeDateTime(DateTime.now());
        this.env["mail.message"].write([message_id], { pinned_at: pinnedAt });
        const notification = `<div data-oe-type="pin" class="o_mail_notification">
                ${this.env.partner.display_name} pinned a
                <a href="#" data-oe-type="highlight" data-oe-id='${message_id}'>message</a> to this channel.
                <a href="#" data-oe-type="pin-menu">See all pinned messages</a>
            </div>`;
        this.message_post(id, {
            body: notification,
            message_type: "notification",
            subtype_xmlid: "mail.mt_comment",
        });
        const [channel] = this.search_read([["id", "=", id]]);
        this.env["bus.bus"]._sendone(channel, "mail.record/insert", {
            Message: {
                id: message_id,
                pinned_at: pinnedAt,
            },
        });
    }

    /**
     * @override
     * @type {typeof models.Model["prototype"]["write"]}
     */
    write(idOrIds, values, kwargs) {
        const [firstId] = ensureArray(idOrIds);
        if ("image_128" in values) {
            super.write(firstId, {
                avatarCacheKey: DateTime.utc().toFormat("yyyyMMddHHmmss"),
            });
            const channel = this.search_read([["id", "=", firstId]])[0];
            return this.env["bus.bus"]._sendone(channel, "mail.record/insert", {
                Thread: {
                    avatarCacheKey: channel.avatarCacheKey,
                    firstId,
                    model: "discuss.channel",
                },
            });
        }

        const notifications = [];
        const [channel] = this._filter([["id", "=", firstId]]);
        if (channel) {
            const diff = {};
            for (const key in values) {
                if (channel[key] != values[key] && key !== "image_128") {
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
            this.env["bus.bus"]._sendmany(notifications);
        }
        return result;
    }

    /**
     * Simulates `_broadcast` on `discuss.channel`.
     *
     * @param {number} id
     * @param {number[]} partner_ids
     */
    _broadcast(ids, partner_ids) {
        const notifications = this._channelChannelNotifications(ids, partner_ids);
        this.env["bus.bus"]._sendmany(notifications);
    }

    /**
     * Simulates `_channel_channel_notifications` on `discuss.channel`.
     *
     * @param {number} id
     * @param {number[]} partner_ids
     */
    _channelChannelNotifications(ids, partner_ids) {
        const notifications = [];
        for (const partner_id of partner_ids) {
            const user = this.env["res.users"]._filter([["partner_id", "in", partner_id]])[0];
            if (!user) {
                continue;
            }
            // Note: `channel_info` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const channelInfos = this.channel_info(ids);
            const [relatedPartner] = this.env["res.partner"].search_read([["id", "=", partner_id]]);
            for (const channelInfo of channelInfos) {
                notifications.push([relatedPartner, "mail.record/insert", { Thread: channelInfo }]);
            }
        }
        return notifications;
    }

    /**
     * Simulates the `_channel_seen` method of `discuss.channel`.
     *
     * @param {number[]} ids
     * @param {number} last_message_id
     */
    _channelSeen(ids, last_message_id) {
        // Update record
        const channel_id = ids[0];
        if (!channel_id) {
            throw new Error("Should only be one channel in channel_seen mock params");
        }
        const channel = this._filter([["id", "=", channel_id]])[0];
        const messages = this.env["mail.message"]._filter([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channel.id],
        ]);
        if (!messages || messages.length === 0) {
            return;
        }
        if (!channel) {
            return;
        }
        this._setLastSeenMessage([channel.id], last_message_id);
        this.env["bus.bus"]._sendone(
            channel.channel_type === "chat" ? channel : this.env.partner,
            "discuss.channel.member/seen",
            {
                channel_id: channel.id,
                last_message_id: last_message_id,
                partner_id: this.env.partner_id,
            }
        );
    }

    /**
     * Simulates the `_set_last_seen_message` method of `discuss.channel`.
     *
     * @param {number[]} ids
     * @param {number} messageId
     */
    _setLastSeenMessage(ids, messageId) {
        const memberOfCurrentUser = this.env["discuss.channel.member"]._getAsSudoFromContext(
            ids[0]
        );
        if (memberOfCurrentUser) {
            this.env["discuss.channel.member"].write([memberOfCurrentUser.id], {
                fetched_message_id: messageId,
                seen_message_id: messageId,
            });
        }
    }

    /**
     * Simulates the `_get_init_channels` method on `discuss.channel`.
     */
    _getInitChannels(user) {
        const members = this.env["discuss.channel.member"]._filter([
            ["partner_id", "=", user.partner_id],
            "|",
            ["fold_state", "in", ["open", "folded"]],
            ["rtc_inviting_session_id", "!=", false],
        ]);
        return this._filter([["id", "in", members.map((m) => m.channel_id)]]);
    }
}
