/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

import { assignDefined } from "@mail/utils/common/misc";
import { formatDate, serializeDateTime, today } from "@web/core/l10n/dates";
import { Command } from "@mail/../tests/helpers/command";
const { DateTime } = luxon;

patch(MockServer.prototype, {
    /**
     * @override
     */
    mockWrite(model, args) {
        const notifications = [];
        const old_info = {};
        if (model == "discuss.channel") {
            Object.assign(old_info, this._mockDiscussChannelBasicInfo(args[0][0]));
        }
        const mockWriteResult = super.mockWrite(...arguments);
        if (model == "discuss.channel") {
            const [channel] = this.getRecords(model, [["id", "=", args[0][0]]]);
            const info = this._mockDiscussChannelBasicInfo(channel.id);
            const diff = {};
            for (const key of Object.keys(info)) {
                if (info[key] !== old_info[key]) {
                    diff[key] = info[key];
                }
            }
            if (Object.keys(diff).length) {
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
        }
        if (notifications.length) {
            this.pyEnv["bus.bus"]._sendmany(notifications);
        }
        return mockWriteResult;
    },
    async _performRPC(route, args) {
        if (args.model === "discuss.channel" && args.method === "execute_command_help") {
            return this._mockDiscussChannelExecuteCommandHelp(args.args[0], args.model);
        }
        if (args.model === "discuss.channel" && args.method === "action_unfollow") {
            const ids = args.args[0];
            return this._mockDiscussChannelActionUnfollow(ids, args.kwargs.context);
        }
        if (args.model === "discuss.channel" && args.method === "channel_fetched") {
            const ids = args.args[0];
            return this._mockDiscussChannelChannelFetched(ids);
        }
        if (args.model === "discuss.channel" && args.method === "channel_fetch_preview") {
            const ids = args.args[0];
            return this._mockDiscussChannelChannelFetchPreview(ids);
        }
        if (args.model === "discuss.channel" && args.method === "channel_fold") {
            const ids = args.args[0];
            const state = args.args[1] || args.kwargs.state;
            const state_count = args.args[2] || args.kwargs.state_count;
            return this._mockDiscussChannelChannelFold(ids, state, state_count);
        }
        if (args.model === "discuss.channel" && args.method === "channel_create") {
            const name = args.args[0];
            const groupId = args.args[1];
            return this._mockDiscussChannelChannelCreate(name, groupId);
        }
        if (args.model === "discuss.channel" && args.method === "set_message_pin") {
            return this._mockDiscussChannelSetMessagePin(
                args.args[0],
                args.kwargs.message_id,
                args.kwargs.pinned
            );
        }
        if (args.model === "discuss.channel" && args.method === "channel_get") {
            const partners_to = args.args[0] || args.kwargs.partners_to;
            const pin =
                args.args[1] !== undefined
                    ? args.args[1]
                    : args.kwargs.pin !== undefined
                    ? args.kwargs.pin
                    : undefined;
            return this._mockDiscussChannelChannelGet(partners_to, pin);
        }
        if (route === "/discuss/channel/info") {
            const id = args.channel_id;
            return this._mockDiscussChannelChannelInfo([id])[0];
        }
        if (args.model === "discuss.channel" && args.method === "add_members") {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            return this._mockDiscussChannelAddMembers(ids, partner_ids, args.kwargs.context);
        }
        if (args.model === "discuss.channel" && args.method === "channel_pin") {
            const ids = args.args[0];
            const pinned = args.args[1] || args.kwargs.pinned;
            return this._mockDiscussChannelChannelPin(ids, pinned);
        }
        if (args.model === "discuss.channel" && args.method === "channel_rename") {
            const ids = args.args[0];
            const name = args.args[1] || args.kwargs.name;
            return this._mockDiscussChannelChannelRename(ids, name);
        }
        if (args.model === "discuss.channel" && args.method === "channel_change_description") {
            const ids = args.args[0];
            const description = args.args[1] || args.kwargs.description;
            return this._mockDiscussChannelChannelChangeDescription(ids, description);
        }
        if (route === "/discuss/channel/set_last_seen_message") {
            const id = args.channel_id;
            const last_message_id = args.last_message_id;
            return this._mockDiscussChannel_ChannelSeen([id], last_message_id);
        }
        if (args.model === "discuss.channel" && args.method === "channel_set_custom_name") {
            const ids = args.args[0];
            const name = args.args[1] || args.kwargs.name;
            return this._mockDiscussChannelChannelSetCustomName(ids, name);
        }
        if (args.model === "discuss.channel" && args.method === "create_group") {
            const partners_to = args.args[0] || args.kwargs.partners_to;
            return this._mockDiscussChannelCreateGroup(partners_to);
        }
        if (args.model === "discuss.channel" && args.method === "execute_command_leave") {
            return this._mockDiscussChannelExecuteCommandLeave(args, args.kwargs?.context);
        }
        if (args.model === "discuss.channel" && args.method === "execute_command_who") {
            return this._mockDiscussChannelExecuteCommandWho(args);
        }
        if (
            args.model === "discuss.channel" &&
            args.method === "write" &&
            "image_128" in args.args[1]
        ) {
            const ids = args.args[0];
            return this._mockDiscussChannelWriteImage128(ids[0]);
        }
        if (args.model === "discuss.channel" && args.method === "load_more_members") {
            const [channel_ids] = args.args;
            const { known_member_ids } = args.kwargs;
            return this._mockDiscussChannelloadOlderMembers(channel_ids, known_member_ids);
        }
        if (args.model === "discuss.channel" && args.method === "get_mention_suggestions") {
            return this._mockDiscussChannelGetMentionSuggestions(args);
        }
        return super._performRPC(route, args);
    },

    /**
     * Simulates `execute_command_help` on `discuss.channel`.
     *
     * @param {number} id
     * @param {Object} [model]
     * @returns
     */
    _mockDiscussChannelExecuteCommandHelp(ids, model) {
        const id = ids[0];
        if (model !== "discuss.channel") {
            return;
        }
        const [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", id]]);
        const notifBody = `
            <span class="o_mail_notification">You are in ${
                channel.channel_type === "channel" ? "channel" : "a private conversation with"
            }
            <b>${
                channel.channel_type === "channel"
                    ? `#${channel.name}`
                    : channel.channel_member_ids.map(
                          (id) =>
                              this.pyEnv["discuss.channel.member"].searchRead([["id", "=", id]])[0]
                                  .name
                      )
            }</b>.<br><br>

            Type <b>@username</b> to mention someone, and grab their attention.<br>
            Type <b>#channel</b> to mention a channel.<br>
            Type <b>/command</b> to execute a command.<br></span>
        `;
        this.pyEnv["bus.bus"]._sendone(
            this.pyEnv.currentPartner,
            "discuss.channel/transient_message",
            {
                body: notifBody,
                model: "discuss.channel",
                res_id: channel.id,
            }
        );
        return true;
    },
    /**
     * Simulates `message_post` on `discuss.channel`.
     *
     * @private
     * @param {integer} id
     * @param {Object} kwargs
     * @param {Object} [context]
     * @returns {integer|false}
     */
    _mockDiscussChannelMessagePost(id, kwargs, context) {
        const message_type = kwargs.message_type || "notification";
        const channel = this.getRecords("discuss.channel", [["id", "=", id]])[0];
        const members = this.pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channel.id],
        ]);
        this.pyEnv["discuss.channel.member"].write(members, {
            last_interest_dt: serializeDateTime(today()),
            is_pinned: true,
        });
        const messageData = this._mockMailThreadMessagePost(
            "discuss.channel",
            [id],
            Object.assign(kwargs, {
                message_type,
            }),
            context
        );
        if (kwargs.author_id === this.pyEnv.currentPartnerId) {
            this._mockDiscussChannel_SetLastSeenMessage([channel.id], messageData.id);
        }
        // simulate compute of message_unread_counter
        const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(
            channel.id
        );
        const otherMembers = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", channel.id],
            ["id", "!=", memberOfCurrentUser?.id || false],
        ]);
        for (const member of otherMembers) {
            this.pyEnv["discuss.channel.member"].write([member.id], {
                message_unread_counter: member.message_unread_counter + 1,
            });
        }
        return messageData;
    },
    /**
     * Simulates `action_unfollow` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockDiscussChannelActionUnfollow(ids) {
        const channel = this.getRecords("discuss.channel", [["id", "in", ids]])[0];
        const [channelMember] = this.getRecords("discuss.channel.member", [
            ["channel_id", "in", ids],
            ["partner_id", "=", this.pyEnv.currentPartnerId],
        ]);
        if (!channelMember) {
            return true;
        }
        this.pyEnv["discuss.channel"].write([channel.id], {
            channel_member_ids: [[2, channelMember.id]],
        });
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "discuss.channel/leave", {
            id: channel.id,
        });
        this.pyEnv["bus.bus"]._sendone(channel, "mail.record/insert", {
            Thread: {
                id: channel.id,
                channelMembers: [["DELETE", { id: channelMember.id }]],
                memberCount: this.pyEnv["discuss.channel.member"].searchCount([
                    ["channel_id", "=", channel.id],
                ]),
                model: "discuss.channel",
            },
        });
        this._mockDiscussChannelMessagePost(channel.id, {
            author_id: this.pyEnv.currentPartnerId,
            body: '<div class="o_mail_notification">left the channel</div>',
            subtype_xmlid: "mail.mt_comment",
        });
        return true;
    },
    /**
     * Simulates `add_members` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     */
    _mockDiscussChannelAddMembers(ids, partner_ids, context = {}) {
        const [channel] = this.getRecords("discuss.channel", [["id", "in", ids]]);
        const partners = this.getRecords("res.partner", [["id", "in", partner_ids]]);
        for (const partner of partners) {
            if (partner.id === this.pyEnv.currentPartnerId) {
                continue; // adding 'yourself' to the conversation is handled below
            }
            const body = `<div class="o_mail_notification">invited ${partner.name} to the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this._mockDiscussChannelMessagePost(channel.id, { body, message_type, subtype_xmlid });
        }
        const insertedChannelMembers = [];
        for (const partner of partners) {
            insertedChannelMembers.push(
                this.pyEnv["discuss.channel.member"].create({
                    channel_id: channel.id,
                    partner_id: partner.id,
                    create_uid: this.pyEnv.currentUserId,
                })
            );
            this.pyEnv["bus.bus"]._sendone(partner, "discuss.channel/joined", {
                channel: this._mockDiscussChannelChannelInfo([channel.id])[0],
                invited_by_user_id: this.pyEnv.currentUserId,
            });
        }
        const selfPartner = partners.find((partner) => partner.id === this.pyEnv.currentPartnerId);
        if (selfPartner) {
            // needs to be done after adding 'self' as a member
            const body = `<div class="o_mail_notification">${selfPartner.name} joined the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this._mockDiscussChannelMessagePost(channel.id, { body, message_type, subtype_xmlid });
        }
        const isSelfMember =
            this.pyEnv["discuss.channel.member"].searchCount([
                ["partner_id", "=", this.pyEnv.currentPartnerId],
                ["channel_id", "=", channel.id],
            ]) > 0;
        if (isSelfMember) {
            this.pyEnv["bus.bus"]._sendone(channel, "mail.record/insert", {
                Thread: {
                    id: channel.id,
                    channelMembers: [
                        [
                            "ADD",
                            this._mockDiscussChannelMember_DiscussChannelMemberFormat(
                                insertedChannelMembers
                            ),
                        ],
                    ],
                    memberCount: this.pyEnv["discuss.channel.member"].searchCount([
                        ["channel_id", "=", channel.id],
                    ]),
                    model: "discuss.channel",
                },
            });
        }
    },
    /**
     * Simulates `set_message_pin` on `discuss.channel`.
     *
     * @param {number} ids
     * @param {number} message_id
     * @param {boolean} pinned
     */
    _mockDiscussChannelSetMessagePin(id, message_id, pinned) {
        const pinnedAt = pinned ? formatDate(luxon.DateTime.now()) : false;
        this.pyEnv["mail.message"].write([message_id], {
            pinned_at: pinnedAt,
        });
        const notification = `<div data-oe-type="pin" class="o_mail_notification">
                ${this.pyEnv.currentPartner.display_name} pinned a
                <a href="#" data-oe-type="highlight" data-oe-id='${message_id}'>message</a> to this channel.
                <a href="#" data-oe-type="pin-menu">See all pinned messages</a>
            </div>`;
        this._mockDiscussChannelMessagePost(id, {
            body: notification,
            message_type: "notification",
            subtype_xmlid: "mail.mt_comment",
        });
        const [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", id]]);
        this.pyEnv["bus.bus"]._sendone(channel, "mail.record/insert", {
            Message: {
                id: message_id,
                pinned_at: pinnedAt,
            },
        });
    },
    /**
     * Simulates `_broadcast` on `discuss.channel`.
     *
     * @private
     * @param {integer} id
     * @param {integer[]} partner_ids
     * @returns {Object}
     */
    _mockDiscussChannel_broadcast(ids, partner_ids) {
        const notifications = this._mockDiscussChannel_channelChannelNotifications(
            ids,
            partner_ids
        );
        this.pyEnv["bus.bus"]._sendmany(notifications);
    },
    /**
     * Simulates `_channel_channel_notifications` on `discuss.channel`.
     *
     * @private
     * @param {integer} id
     * @param {integer[]} partner_ids
     * @returns {Object}
     */
    _mockDiscussChannel_channelChannelNotifications(ids, partner_ids) {
        const notifications = [];
        for (const partner_id of partner_ids) {
            const user = this.getRecords("res.users", [["partner_id", "in", partner_id]])[0];
            if (!user) {
                continue;
            }
            // Note: `channel_info` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const channelInfos = this._mockDiscussChannelChannelInfo(ids);
            const [relatedPartner] = this.pyEnv["res.partner"].searchRead([
                ["id", "=", partner_id],
            ]);
            for (const channelInfo of channelInfos) {
                notifications.push([relatedPartner, "mail.record/insert", { Thread: channelInfo }]);
            }
        }
        return notifications;
    },
    /**
     * Simulates `channel_fetched` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {string} extra_info
     */
    _mockDiscussChannelChannelFetched(ids) {
        const channels = this.getRecords("discuss.channel", [["id", "in", ids]]);
        for (const channel of channels) {
            if (!["chat", "whatsapp"].includes(channel.channel_type)) {
                continue;
            }
            const channelMessages = this.getRecords("mail.message", [
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
            const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(
                channel.id
            );
            this.pyEnv["discuss.channel.member"].write([memberOfCurrentUser.id], {
                fetched_message_id: lastMessage.id,
            });
            this.pyEnv["bus.bus"]._sendone(channel, "discuss.channel.member/fetched", {
                channel_id: channel.id,
                id: memberOfCurrentUser.id,
                last_message_id: lastMessage.id,
                partner_id: this.pyEnv.currentPartnerId,
            });
        }
    },
    /**
     * Simulates `channel_fetch_preview` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]} list of channels previews
     */
    _mockDiscussChannelChannelFetchPreview(ids) {
        const channels = this.getRecords("discuss.channel", [["id", "in", ids]]);
        return channels
            .map((channel) => {
                const channelMessages = this.getRecords("mail.message", [
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
                        ? this._mockMailMessageMessageFormat([lastMessage.id])[0]
                        : false,
                };
            })
            .filter((preview) => preview.last_message);
    },
    /**
     * Simulates the 'channel_fold' route on `discuss.channel`.
     * In particular sends a notification on the bus.
     *
     * @private
     * @param {number} ids
     * @param {state} [state]
     * @param {number} [state_count]
     */
    _mockDiscussChannelChannelFold(ids, state, state_count) {
        const channels = this.getRecords("discuss.channel", [["id", "in", ids]]);
        for (const channel of channels) {
            const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(
                channel.id
            );
            const foldState = state
                ? state
                : memberOfCurrentUser.fold_state === "open"
                ? "folded"
                : "open";
            const vals = {
                fold_state: foldState,
                is_minimized: foldState !== "closed",
            };
            this.pyEnv["discuss.channel.member"].write([memberOfCurrentUser.id], vals);
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "discuss.Thread/fold_state", {
                foldStateCount: state_count,
                id: channel.id,
                model: "discuss.channel",
                fold_state: foldState,
            });
        }
    },
    /**
     * Simulates 'channel_create' on 'discuss.channel'.
     *
     * @private
     * @param {string} name
     * @param {string} [group_id]
     * @returns {Object}
     */
    _mockDiscussChannelChannelCreate(name, group_id) {
        const id = this.pyEnv["discuss.channel"].create({
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        partner_id: this.pyEnv.currentPartnerId,
                    },
                ],
            ],
            channel_type: "channel",
            name,
            group_public_id: group_id,
        });
        this.pyEnv["discuss.channel"].write([id], {
            group_public_id: group_id,
        });
        this._mockDiscussChannelMessagePost(id, {
            body: `<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="${id}">#${name}</a></div>`,
            message_type: "notification",
        });
        this._mockDiscussChannel_broadcast(id, [this.pyEnv.currentPartner]);
        return this._mockDiscussChannelChannelInfo([id])[0];
    },
    /**
     * Simulates 'channel_get' on 'discuss.channel'.
     *
     * @private
     * @param {integer[]} [partners_to=[]]
     * @param {boolean} [pin=true]
     * @returns {Object}
     */
    _mockDiscussChannelChannelGet(partners_to = [], pin = true) {
        if (partners_to.length === 0) {
            return false;
        }
        if (!partners_to.includes(this.pyEnv.currentPartnerId)) {
            partners_to.push(this.pyEnv.currentPartnerId);
        }
        const partners = this.getRecords("res.partner", [["id", "in", partners_to]]);
        const channels = this.pyEnv["discuss.channel"].searchRead([["channel_type", "=", "chat"]]);
        for (const channel of channels) {
            const channelMemberIds = this.pyEnv["discuss.channel.member"].search([
                ["channel_id", "=", channel.id],
                ["partner_id", "in", partners_to],
            ]);
            if (
                channelMemberIds.length === partners.length &&
                channel.channel_member_ids.length === partners.length
            ) {
                return this._mockDiscussChannelChannelInfo([channel.id])[0];
            }
        }
        const id = this.pyEnv["discuss.channel"].create({
            channel_member_ids: partners.map((partner) => [
                0,
                0,
                {
                    partner_id: partner.id,
                },
            ]),
            channel_type: "chat",
            name: partners.map((partner) => partner.name).join(", "),
        });
        this._mockDiscussChannel_broadcast(
            id,
            partners.map(({ id }) => id)
        );
        return this._mockDiscussChannelChannelInfo([id])[0];
    },
    /**
     * Simulates `_channel_basic_info` on `discuss.channel`.
     *
     * @private
     * @param {integer} id
     * @returns {Object[]}
     */
    _mockDiscussChannelBasicInfo(id) {
        const [channel] = this.getRecords("discuss.channel", [["id", "=", id]]);
        const [group_public_id] = this.getRecords("res.groups", [
            ["id", "=", channel.group_public_id],
        ]);
        const res = assignDefined({}, channel, [
            "allow_public_upload",
            "avatarCacheKey",
            "channel_type",
            "create_uid",
            "defaultDisplayMode",
            "description",
            "group_based_subscription",
            "id",
            "name",
            "uuid",
        ]);
        Object.assign(res, {
            memberCount: this.pyEnv["discuss.channel.member"].searchCount([
                ["channel_id", "=", channel.id],
            ]),
            authorizedGroupFullName: group_public_id ? group_public_id.name : false,
            model: "discuss.channel",
        });
        return res;
    },
    /**
     * Simulates `channel_info` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]}
     */
    _mockDiscussChannelChannelInfo(ids) {
        const channels = this.getRecords("discuss.channel", [["id", "in", ids]]);
        return channels.map((channel) => {
            const members = this.getRecords("discuss.channel.member", [
                ["id", "in", channel.channel_member_ids],
            ]);
            const res = this._mockDiscussChannelBasicInfo(channel.id);
            const messages = this.getRecords("mail.message", [
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channel.id],
            ]);
            const messageNeedactionCounter = this.getRecords("mail.notification", [
                ["res_partner_id", "=", this.pyEnv.currentPartnerId],
                ["is_read", "=", false],
                ["mail_message_id", "in", messages.map((message) => message.id)],
            ]).length;
            res.message_needaction_counter = messageNeedactionCounter;
            const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(
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
                    res["rtc_inviting_session"] = {
                        id: memberOfCurrentUser.rtc_inviting_session_id,
                    };
                }
                res["channelMembers"] = [
                    [
                        "ADD",
                        this._mockDiscussChannelMember_DiscussChannelMemberFormat([
                            memberOfCurrentUser.id,
                        ]),
                    ],
                ];
            }
            if (channel.channel_type !== "channel") {
                res["seen_partners_info"] = members.map((member) => {
                    return {
                        id: member.id,
                        [member.partner_id ? "partner_id" : "guest_id"]:
                            member.partner_id || member.guest_id,
                        seen_message_id: member.seen_message_id,
                        fetched_message_id: member.fetched_message_id,
                    };
                });
                res["channelMembers"] = [
                    [
                        "ADD",
                        this._mockDiscussChannelMember_DiscussChannelMemberFormat(
                            members.map((member) => member.id)
                        ),
                    ],
                ];
            }
            let is_editable;
            switch (channel.channel_type) {
                case "channel":
                    is_editable = channel.create_uid === this.pyEnv.currentUserId;
                    break;
                case "group":
                    is_editable = memberOfCurrentUser;
                    break;
                default:
                    is_editable = false;
                    break;
            }
            res.is_editable = is_editable;
            res["rtcSessions"] = [
                [
                    "ADD",
                    (channel.rtc_session_ids || []).map((rtcSessionId) =>
                        this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(
                            rtcSessionId,
                            { extra: true }
                        )
                    ),
                ],
            ];
            return res;
        });
    },
    /**
     * Simulates the `channel_pin` method of `discuss.channel`.
     *
     * @private
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     */
    async _mockDiscussChannelChannelPin(ids, pinned = false) {
        const [channel] = this.getRecords("discuss.channel", [["id", "in", ids]]);
        const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(
            channel.id
        );
        if (memberOfCurrentUser && memberOfCurrentUser.is_pinned !== pinned) {
            this.pyEnv["discuss.channel.member"].write([memberOfCurrentUser.id], {
                is_pinned: pinned,
            });
        }
        if (!pinned) {
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "discuss.channel/unpin", {
                id: channel.id,
            });
        } else {
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.record/insert", {
                Thread: this._mockDiscussChannelChannelInfo([channel.id])[0],
            });
        }
    },
    /**
     * Simulates the `_channel_seen` method of `discuss.channel`.
     *
     * @private
     * @param integer[] ids
     * @param {integer} last_message_id
     */
    async _mockDiscussChannel_ChannelSeen(ids, last_message_id) {
        // Update record
        const channel_id = ids[0];
        if (!channel_id) {
            throw new Error("Should only be one channel in channel_seen mock params");
        }
        const channel = this.getRecords("discuss.channel", [["id", "=", channel_id]])[0];
        const messages = this.getRecords("mail.message", [
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channel.id],
        ]);
        if (!messages || messages.length === 0) {
            return;
        }
        if (!channel) {
            return;
        }
        this._mockDiscussChannel_SetLastSeenMessage([channel.id], last_message_id);
    },
    /**
     * Simulates `channel_rename` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockDiscussChannelChannelRename(ids, name) {
        const channel = this.getRecords("discuss.channel", [["id", "in", ids]])[0];
        this.pyEnv["discuss.channel"].write([channel.id], { name });
    },
    _mockDiscussChannelChannelChangeDescription(ids, description) {
        const channel = this.getRecords("discuss.channel", [["id", "in", ids]])[0];
        this.pyEnv["discuss.channel"].write([channel.id], { description });
    },
    /**
     * Simulates `channel_set_custom_name` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockDiscussChannelChannelSetCustomName(ids, name) {
        const channelId = ids[0]; // simulate ensure_one.
        const [memberIdOfCurrentUser] = this.pyEnv["discuss.channel.member"].search([
            ["partner_id", "=", this.pyEnv.currentPartnerId],
            ["channel_id", "=", channelId],
        ]);
        this.pyEnv["discuss.channel.member"].write([memberIdOfCurrentUser], {
            custom_channel_name: name,
        });
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.record/insert", {
            Thread: {
                custom_channel_name: name,
                id: channelId,
                model: "discuss.channel",
            },
        });
    },
    /**
     * Simulates the `create_group` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} partners_to
     * @returns {Object}
     */
    async _mockDiscussChannelCreateGroup(partners_to) {
        const partners = this.getRecords("res.partner", [["id", "in", partners_to]]);
        const id = this.pyEnv["discuss.channel"].create({
            channel_type: "group",
            channel_member_ids: partners.map((partner) =>
                Command.create({ partner_id: partner.id })
            ),
            name: "",
        });
        this._mockDiscussChannel_broadcast(
            id,
            partners.map((partner) => partner.id)
        );
        return this._mockDiscussChannelChannelInfo([id])[0];
    },
    /**
     * Simulates `execute_command_leave` on `discuss.channel`.
     *
     * @private
     */
    _mockDiscussChannelExecuteCommandLeave(args, context = {}) {
        const channel = this.getRecords("discuss.channel", [["id", "in", args.args[0]]])[0];
        if (channel.channel_type === "channel") {
            this._mockDiscussChannelActionUnfollow([channel.id], context);
        } else {
            this._mockDiscussChannelChannelPin([channel.id], false);
        }
    },
    /**
     * Simulates `execute_command_who` on `discuss.channel`.
     *
     * @private
     */
    _mockDiscussChannelExecuteCommandWho(args) {
        const ids = args.args[0];
        const channels = this.getRecords("discuss.channel", [["id", "in", ids]]);
        for (const channel of channels) {
            const members = this.getRecords("discuss.channel.member", [
                ["id", "in", channel.channel_member_ids],
            ]);
            const otherPartnerIds = members
                .filter(
                    (member) =>
                        member.partner_id && member.partner_id !== this.pyEnv.currentPartnerId
                )
                .map((member) => member.partner_id);
            const otherPartners = this.getRecords("res.partner", [["id", "in", otherPartnerIds]]);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners
                    .map((partner) => partner.name)
                    .join(", ")} and you`;
            }
            this.pyEnv["bus.bus"]._sendone(
                this.pyEnv.currentPartner,
                "discuss.channel/transient_message",
                {
                    body: `<span class="o_mail_notification">${message}</span>`,
                    model: "discuss.channel",
                    res_id: channel.id,
                }
            );
        }
    },
    /**
     * Simulates `get_mention_suggestions` on `discuss.channel`.
     *
     * @private
     * @returns {Array[]}
     */
    _mockDiscussChannelGetMentionSuggestions(args) {
        const search = args.kwargs.search || "";
        const limit = args.kwargs.limit || 8;

        /**
         * Returns the given list of channels after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {Object[]} channels
         * @param {string} search
         * @param {integer} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = function (channels, search, limit) {
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
                        id: channel.id,
                        model: "discuss.channel",
                        name: channel.name,
                    };
                });
            // reduce results to max limit
            matchingChannels.length = Math.min(matchingChannels.length, limit);
            return matchingChannels;
        };

        const mentionSuggestions = mentionSuggestionsFilter(
            this.models["discuss.channel"].records,
            search,
            limit
        );

        return mentionSuggestions;
    },
    /**
     * Simulates `write` on `discuss.channel` when `image_128` changes.
     *
     * @param {integer} id
     */
    _mockDiscussChannelWriteImage128(id) {
        this.pyEnv["discuss.channel"].write([id], {
            avatarCacheKey: DateTime.utc().toFormat("yyyyMMddHHmmss"),
        });
        const channel = this.pyEnv["discuss.channel"].searchRead([["id", "=", id]])[0];
        this.pyEnv["bus.bus"]._sendone(channel, "mail.record/insert", {
            Thread: {
                avatarCacheKey: channel.avatarCacheKey,
                id,
                model: "discuss.channel",
            },
        });
    },
    /**
     * Simulates `load_more_members` on `discuss.channel`.
     *
     * @private
     * @param {integer[]} channel_ids
     * @param {integer[]} known_member_ids
     */
    _mockDiscussChannelloadOlderMembers(channel_ids, known_member_ids) {
        const members = this.pyEnv["discuss.channel.member"].searchRead(
            [
                ["id", "not in", known_member_ids],
                ["channel_id", "in", channel_ids],
            ],
            { limit: 100 }
        );
        const memberCount = this.pyEnv["discuss.channel.member"].searchCount([
            ["channel_id", "in", channel_ids],
        ]);
        const membersData = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                const [partner] = this.pyEnv["res.partner"].searchRead(
                    [["id", "=", member.partner_id[0]]],
                    { fields: ["id", "name", "im_status"], context: { active_test: false } }
                );
                persona = {
                    id: partner.id,
                    name: partner.name,
                    im_status: partner.im_status,
                    type: "partner",
                };
            }
            if (member.guest_id) {
                const [guest] = this.pyEnv["mail.guest"].searchRead(
                    [["id", "=", member.guest_id[0]]],
                    { fields: ["id", "name"] }
                );
                persona = {
                    id: guest.id,
                    name: guest.name,
                    type: "guest",
                };
            }
            membersData.push({
                id: member.id,
                persona: persona,
            });
        }
        return {
            channelMembers: [["ADD", membersData]],
            memberCount,
        };
    },
    /**
     * Simulates the `_set_last_seen_message` method of `discuss.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer} message_id
     */
    _mockDiscussChannel_SetLastSeenMessage(ids, message_id) {
        const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(ids[0]);
        if (memberOfCurrentUser) {
            this.pyEnv["discuss.channel.member"].write([memberOfCurrentUser.id], {
                fetched_message_id: message_id,
                seen_message_id: message_id,
            });
        }
        const [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "in", ids]]);
        const [partner, guest] = this._mockResPartner__getCurrentPersona();
        let target = guest ?? partner;
        if (this._mockDiscussChannel__typesAllowingSeenInfos().includes(channel.channel_type)) {
            target = channel;
        }
        this.pyEnv["bus.bus"]._sendone(target, "discuss.channel.member/seen", {
            channel_id: channel.id,
            id: memberOfCurrentUser?.id,
            last_message_id: message_id,
            [guest ? "guest_id" : "partner_id"]: guest?.id ?? partner.id,
        });
    },
    /**
     * Simulates `_types_allowing_seen_infos` on `discuss.channel`.
     *
     * @returns {string[]}
     */
    _mockDiscussChannel__typesAllowingSeenInfos() {
        return ["chat", "group"];
    },
});
