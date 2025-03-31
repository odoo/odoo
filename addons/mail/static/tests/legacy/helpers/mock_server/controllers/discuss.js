/** @odoo-module alias=@mail/../tests/helpers/mock_server/controllers/discuss default=false */

import { serializeDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

const { DateTime } = luxon;

patch(MockServer.prototype, {
    /**
     * @override
     */
    async performRPC(route, args) {
        if (route === "/mail/attachment/upload") {
            const ufile = args.body.get("ufile");
            const is_pending = args.body.get("is_pending") === "true";
            const model = is_pending ? "mail.compose.message" : args.body.get("thread_model");
            const id = is_pending ? 0 : parseInt(args.body.get("thread_id"));
            const attachmentId = this.mockCreate("ir.attachment", {
                // datas,
                mimetype: ufile.type,
                name: ufile.name,
                res_id: id,
                res_model: model,
            });
            if (args.body.get("voice")) {
                this.mockCreate("discuss.voice.metadata", { attachment_id: attachmentId });
            }
            return {
                data: { "ir.attachment": this._mockIrAttachment_attachmentFormat([attachmentId]) },
            };
        }
        return super.performRPC(...arguments);
    },
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === "/mail/attachment/delete") {
            const { attachment_id } = args;
            return this._mockRouteMailAttachmentRemove(attachment_id);
        }
        if (route === "/discuss/channel/messages") {
            const { search_term, channel_id, after, around, before, limit } = args;
            return this._mockRouteDiscussChannelMessages(
                channel_id,
                search_term,
                before,
                after,
                around,
                limit
            );
        }
        if (route === "/discuss/channel/mute") {
            const { channel_id, minutes } = args;
            return this._mockRouteDiscussChannelMute(channel_id, minutes);
        }
        if (route === "/discuss/channel/pinned_messages") {
            const { channel_id } = args;
            return this._mockRouteDiscussChannelPins(channel_id);
        }
        if (route === "/discuss/channel/notify_typing") {
            const id = args.channel_id;
            const is_typing = args.is_typing;
            return this._mockRouteDiscussChannelNotifyTyping(id, is_typing);
        }
        if (route === "/discuss/channel/ping") {
            return;
        }
        if (route === "/discuss/channel/members") {
            const { channel_id, known_member_ids } = args;
            return this._mockDiscussChannelloadOlderMembers([channel_id], known_member_ids);
        }
        if (route === "/mail/history/messages") {
            const { search_term, after, before, limit } = args;
            return this._mockRouteMailMessageHistory(search_term, after, before, limit);
        }
        if (route === "/mail/inbox/messages") {
            return { count: 0, data: {}, message: [] };
        }
        if (route === "/mail/link_preview") {
            return this._mockRouteMailLinkPreview(args.message_id);
        }
        if (route === "/mail/link_preview/hide") {
            const linkPreviews = this.pyEnv["mail.link.preview"].search_read([
                ["id", "in", args.link_preview_ids],
            ]);
            for (const linkPreview of linkPreviews) {
                this.pyEnv["bus.bus"]._sendone(
                    this._mockMailMessage__busNotificationTarget(linkPreview.message_id[0]),
                    "mail.record/insert",
                    {
                        "mail.message": {
                            id: linkPreview.message_id[0],
                            linkPreviews: [["DELETE", [{ id: linkPreview.id }]]],
                        },
                    }
                );
            }
            return args;
        }
        if (route === "/mail/message/post") {
            const finalData = {};
            for (const allowedField of [
                "attachment_ids",
                "body",
                "message_type",
                "partner_ids",
                "subtype_xmlid",
                "parent_id",
                "partner_emails",
                "partner_additional_values",
            ]) {
                if (args.post_data[allowedField] !== undefined) {
                    finalData[allowedField] = args.post_data[allowedField];
                }
            }
            if (args.thread_model === "discuss.channel") {
                return this._mockDiscussChannelMessagePost(args.thread_id, finalData, args.context);
            }
            return this._mockMailThreadMessagePost(
                args.thread_model,
                [args.thread_id],
                finalData,
                args.context
            );
        }
        if (route === "/mail/message/reaction") {
            return this._mockRouteMailMessageReaction(args);
        }
        if (route === "/mail/message/update_content") {
            this.pyEnv["mail.message"].write([args.message_id], {
                body: args.body,
                attachment_ids: args.attachment_ids,
            });
            this.pyEnv["bus.bus"]._sendone(
                this._mockMailMessage__busNotificationTarget(args.message_id),
                "mail.record/insert",
                {
                    "mail.message": {
                        id: args.message_id,
                        body: args.body,
                        attachment_ids: this._mockIrAttachment_attachmentFormat(
                            args.attachment_ids
                        ),
                    },
                }
            );
            return { "mail.message": this._mockMailMessageMessageFormat([args.message_id]) };
        }
        if (route === "/mail/partner/from_email") {
            return this._mockRouteMailPartnerFromEmail(args.emails, args.additional_values);
        }
        if (route === "/mail/read_subscription_data") {
            const follower_id = args.follower_id;
            return this._mockRouteMailReadSubscriptionData(follower_id);
        }
        if (route === "/mail/rtc/channel/join_call") {
            return this._mockRouteMailRtcChannelJoinCall(
                args.channel_id,
                args.check_rtc_session_ids
            );
        }
        if (route === "/mail/rtc/channel/leave_call") {
            return this._mockRouteMailRtcChannelLeaveCall(args.channel_id);
        }
        if (route === "/mail/rtc/session/update_and_broadcast") {
            return this._mockRouteMailRtcSessionUpdateAndBroadcast(args.session_id, args.values);
        }
        if (route === "/mail/starred/messages") {
            const { search_term, after, before, limit } = args;
            return this._mockRouteMailMessageStarredMessages(search_term, after, before, limit);
        }
        if (route === "/mail/thread/data") {
            return this._mockRouteMailThreadData(
                args.thread_model,
                args.thread_id,
                args.request_list
            );
        }
        if (route === "/mail/thread/messages") {
            const { search_term, after, around, before, limit, thread_model, thread_id } = args;
            return this._mockRouteMailThreadFetchMessages(
                thread_model,
                thread_id,
                search_term,
                before,
                after,
                around,
                limit
            );
        }
        if (route === "/discuss/gif/favorites") {
            return [[]];
        }
        return super._performRPC(route, args);
    },
    /**
     * Simulates the `/discuss/channel/pinned_messages` route.
     */
    _mockRouteDiscussChannelPins(channel_id) {
        const messageIds = this.pyEnv["mail.message"].search([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channel_id],
            ["pinned_at", "!=", false],
        ]);
        return { "mail.message": this._mockMailMessageMessageFormat(messageIds) };
    },
    /**
     * Simulates the `/mail/attachment/delete` route.
     *
     * @private
     * @param {integer} attachment_id
     */
    async _mockRouteMailAttachmentRemove(attachment_id) {
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "ir.attachment/delete", {
            id: attachment_id,
        });
        return this.pyEnv["ir.attachment"].unlink([attachment_id]);
    },
    /**
     * Simulates the `/discuss/channel/messages` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} limit
     * @param {integer} before
     * @param {integer} after
     * @param {integer} around
     * @returns {Object} list of messages
     */
    async _mockRouteDiscussChannelMessages(
        channel_id,
        search_term = false,
        before = false,
        after = false,
        around = false,
        limit = 30
    ) {
        const domain = [
            ["res_id", "=", channel_id],
            ["model", "=", "discuss.channel"],
            ["message_type", "!=", "user_notification"],
        ];
        const res = this._mockMailMessage_MessageFetch(
            domain,
            search_term,
            before,
            after,
            around,
            limit
        );
        if (!around) {
            this._mockMailMessageSetMessageDone(res.messages.map((message) => message.id));
        }
        return {
            ...res,
            data: {
                "mail.message": this._mockMailMessageMessageFormat(
                    res.messages.map((message) => message.id)
                ),
            },
            "mail.message": res.messages.map((message) => ({ id: message.id })),
        };
    },
    /**
     * Simulates the `/discuss/channel/mute` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} minutes
     */
    _mockRouteDiscussChannelMute(channel_id, minutes) {
        const member = this._mockDiscussChannelMember__getAsSudoFromContext(channel_id);
        let mute_until_dt;
        if (minutes === -1) {
            mute_until_dt = serializeDateTime(DateTime.fromISO("9999-12-31T23:59:59"));
        } else if (minutes) {
            mute_until_dt = serializeDateTime(DateTime.now().plus({ minutes }));
        } else {
            mute_until_dt = false;
        }
        this.pyEnv["discuss.channel.member"].write([member.id], { mute_until_dt });
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.record/insert", {
            "discuss.channel": [{ id: member.channel_id[0], mute_until_dt }],
        });
        return "dummy";
    },
    /**
     * Simulates the `/discuss/channel/notify_typing` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} limit
     * @param {Object} [context={}]
     */
    async _mockRouteDiscussChannelNotifyTyping(channel_id, is_typing) {
        const memberOfCurrentUser =
            this._mockDiscussChannelMember__getAsSudoFromContext(channel_id);
        if (!memberOfCurrentUser) {
            return;
        }
        this._mockDiscussChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
    /**
     * Simulates `/mail/link_preview` route.
     *
     * @private
     * @param {integer} message_id
     * @returns {Object}
     */
    _mockRouteMailLinkPreview(message_id) {
        const linkPreviews = [];
        const [message] = this.pyEnv["mail.message"].search_read([["id", "=", message_id]]);
        if (message.body.includes("https://make-link-preview.com")) {
            const linkPreviewId = this.pyEnv["mail.link.preview"].create({
                message_id: message.id,
                og_description: "test description",
                og_title: "Article title",
                og_type: "article",
                source_url: "https://make-link-preview.com",
            });
            const [linkPreview] = this.pyEnv["mail.link.preview"].search_read([
                ["id", "=", linkPreviewId],
            ]);
            linkPreviews.push(this._mockMailLinkPreviewFormat(linkPreview));
            this.pyEnv["bus.bus"]._sendone(
                this._mockMailMessage__busNotificationTarget(message_id),
                "mail.record/insert",
                { "mail.link.preview": linkPreviews }
            );
        }
    },
    /**
     * Simulates `/mail/message/reaction` route.
     */
    _mockRouteMailMessageReaction({ action, content, message_id }) {
        return this._mockMailMessage_messageReaction(message_id, content, action);
    },
    /**
     * Simulates the `/mail/history/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageHistory(search_term = false, after = false, before = false, limit = 30) {
        const domain = [["needaction", "=", false]];
        const res = this._mockMailMessage_MessageFetch(
            domain,
            search_term,
            before,
            after,
            false,
            limit
        );
        const messagesWithNotification = res.messages.filter((message) => {
            const notifs = this.pyEnv["mail.notification"].search_read([
                ["mail_message_id", "=", message.id],
                ["is_read", "=", true],
                ["res_partner_id", "=", this.pyEnv.currentPartnerId],
            ]);
            return notifs.length > 0;
        });

        return {
            ...res,
            data: {
                "mail.message": this._mockMailMessageMessageFormat(
                    messagesWithNotification.map((message) => message.id)
                ),
            },
            message: res.messages.map((message) => ({ id: message.id })),
        };
    },
    /**
     * Simulates the `/mail/starred/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageStarredMessages(
        search_term = false,
        after = false,
        before = false,
        limit = 30
    ) {
        const domain = [["starred_partner_ids", "in", [this.pyEnv.currentPartnerId]]];
        const res = this._mockMailMessage_MessageFetch(
            domain,
            search_term,
            before,
            after,
            false,
            limit
        );
        return {
            ...res,
            data: {
                "mail.message": this._mockMailMessageMessageFormat(
                    res.messages.map((message) => message.id)
                ),
            },
            message: res.messages.map((message) => ({ id: message.id })),
        };
    },
    /**
     * Simulates the `/mail/partner/from_email` route.
     *
     * @private
     * @param {string[]} emails
     * @returns {Object[]} list of partner data
     */
    _mockRouteMailPartnerFromEmail(emails, additional_values = {}) {
        const partners = emails.map(
            (email) => this.pyEnv["res.partner"].search([["email", "=", email]])[0]
        );
        for (const index in partners) {
            if (!partners[index]) {
                const email = emails[index];
                partners[index] = this.pyEnv["res.partner"].create({
                    email,
                    name: email,
                    ...(additional_values[email] || {}),
                });
            }
        }
        return partners.map((partner_id) => {
            const partner = this.getRecords("res.partner", [["id", "=", partner_id]])[0];
            return { id: partner_id, name: partner.name, email: partner.email };
        });
    },
    /**
     * Simulates the `/mail/read_subscription_data` route.
     *
     * @private
     * @param {integer} follower_id
     * @returns {Object[]} list of followed subtypes
     */
    async _mockRouteMailReadSubscriptionData(follower_id) {
        const follower = this.getRecords("mail.followers", [["id", "=", follower_id]])[0];
        const subtypes = this.getRecords("mail.message.subtype", [
            "&",
            ["hidden", "=", false],
            "|",
            ["res_model", "=", follower.res_model],
            ["res_model", "=", false],
        ]);
        const subtypes_list = subtypes.map((subtype) => {
            const parent = this.getRecords("mail.message.subtype", [
                ["id", "=", subtype.parent_id],
            ])[0];
            return {
                default: subtype.default,
                followed: follower.subtype_ids.includes(subtype.id),
                id: subtype.id,
                internal: subtype.internal,
                name: subtype.name,
                parent_model: parent ? parent.res_model : false,
                res_model: subtype.res_model,
                sequence: subtype.sequence,
            };
        });
        // NOTE: server is also doing a sort here, not reproduced for simplicity
        return subtypes_list;
    },
    /**
     * Simulates the `/mail/rtc/channel/join_call` route.
     *
     * @private
     * @param {integer} channel_id
     * @returns {integer[]} [check_rtc_session_ids]
     */
    async _mockRouteMailRtcChannelJoinCall(channel_id, check_rtc_session_ids = []) {
        const memberOfCurrentUser =
            this._mockDiscussChannelMember__getAsSudoFromContext(channel_id);
        const sessionId = this.pyEnv["discuss.channel.rtc.session"].create({
            channel_member_id: memberOfCurrentUser.id,
            channel_id, // on the server, this is a related field from channel_member_id and not explicitly set
            guest_id: memberOfCurrentUser.guest_id[0],
            partner_id: memberOfCurrentUser.partner_id[0],
        });
        const channelMembers = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", channel_id],
        ]);
        const rtcSessions = this.getRecords("discuss.channel.rtc.session", [
            ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
        ]);
        return {
            iceServers: false,
            rtcSessions: [
                [
                    "ADD",
                    rtcSessions.map((rtcSession) =>
                        this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(
                            rtcSession.id
                        )
                    ),
                ],
            ],
            sessionId: sessionId,
        };
    },
    /**
     * Simulates the `/mail/rtc/channel/leave_call` route.
     *
     * @private
     * @param {integer} channelId
     */
    async _mockRouteMailRtcChannelLeaveCall(channel_id) {
        const channelMembers = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", channel_id],
        ]);
        const rtcSessions = this.getRecords("discuss.channel.rtc.session", [
            ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
        ]);
        const notifications = [];
        const channelInfo =
            this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormatByChannel(
                rtcSessions.map((rtcSession) => rtcSession.id)
            );
        for (const [channelId, sessionsData] of Object.entries(channelInfo)) {
            const channel = this.pyEnv["discuss.channel"].search_read([
                ["id", "=", parseInt(channelId)],
            ])[0];
            const notificationRtcSessions = sessionsData.map((sessionsDataPoint) => {
                return { id: sessionsDataPoint.id };
            });
            notifications.push([
                channel,
                "mail.record/insert",
                {
                    "discuss.channel": [
                        {
                            id: Number(channelId), // JS object keys are strings, but the type from the server is number
                            rtcSessions: [["DELETE", notificationRtcSessions]],
                        },
                    ],
                },
            ]);
        }
        for (const rtcSession of rtcSessions) {
            const target = rtcSession.guest_id
                ? this.pyEnv["mail.guest"].search_read([["id", "=", rtcSession.guest_id]])[0]
                : this.pyEnv["res.partner"].search_read([["id", "=", rtcSession.partner_id]])[0];
            notifications.push([
                target,
                "discuss.channel.rtc.session/ended",
                { sessionId: rtcSession.id },
            ]);
        }
        this.pyEnv["bus.bus"]._sendmany(notifications);
    },
    /**
     * Simulates the `/mail/rtc/session/update_and_broadcast` route.
     *
     * @param {number} session_id
     * @param {object} values
     */
    async _mockRouteMailRtcSessionUpdateAndBroadcast(session_id, values) {
        const [session] = this.pyEnv["discuss.channel.rtc.session"].search_read([
            ["id", "=", session_id],
        ]);
        const [currentChannelMember] = this.pyEnv["discuss.channel.member"].search_read([
            ["id", "=", session.channel_member_id[0]],
        ]);
        if (session && currentChannelMember.partner_id[0] === this.pyEnv.currentPartnerId) {
            this._mockDiscussChannelRtcSession__updateAndBroadcast(session.id, values);
        }
    },
    /**
     * Simulates the `/mail/thread/data` route.
     *
     * @param {string} thread_model
     * @param {integer} thread_id
     * @param {string[]} request_list
     * @returns {Object}
     */
    async _mockRouteMailThreadData(thread_model, thread_id, request_list) {
        const res = {
            hasWriteAccess: true, // mimic user with write access by default
            hasReadAccess: true,
            id: thread_id,
            model: thread_model,
        };
        const thread = this.pyEnv[thread_model].search_read([["id", "=", thread_id]])[0];
        if (!thread) {
            res["hasReadAccess"] = false;
            return res;
        }
        res["canPostOnReadonly"] = thread_model === "discuss.channel"; // model that have attr _mail_post_access='read'
        if (
            request_list.includes("activities") &&
            this.pyEnv.mockServer.models[thread_model].has_activities
        ) {
            const activities = this.pyEnv["mail.activity"].search_read([
                ["id", "in", thread.activity_ids || []],
            ]);
            res["activities"] = this._mockMailActivityActivityFormat(
                activities.map((activity) => activity.id)
            );
        }
        if (request_list.includes("attachments")) {
            const attachments = this.pyEnv["ir.attachment"].search_read([
                ["res_id", "=", thread.id],
                ["res_model", "=", thread_model],
            ]); // order not done for simplicity
            res["attachments"] = this._mockIrAttachment_attachmentFormat(
                attachments.map((attachment) => attachment.id)
            );
            // Specific implementation of mail.thread.main.attachment
            if (this.models[thread_model].fields["message_main_attachment_id"]) {
                res["mainAttachment"] = thread.message_main_attachment_id
                    ? { id: thread.message_main_attachment_id[0] }
                    : false;
            }
        }
        if (request_list.includes("followers")) {
            res["followersCount"] = (thread.message_follower_ids || []).length;
            res["selfFollower"] = false;
            res["recipientsCount"] = (thread.message_follower_ids || []).length - 1;
        }
        if (request_list.includes("suggestedRecipients")) {
            res["suggestedRecipients"] = this._mockMailThread_MessageGetSuggestedRecipients(
                thread_model,
                thread.id
            );
        }
        return { "mail.thread": [res] };
    },
    /**
     * Simulates the `/mail/thread/messages` route.
     *
     * @private
     * @param {string} res_model
     * @param {integer} res_id
     * @param {integer} before
     * @param {integer} after
     * @param {integer} limit
     * @returns {Object[]} list of messages
     */
    async _mockRouteMailThreadFetchMessages(
        res_model,
        res_id,
        search_term = false,
        before = false,
        after = false,
        around = false,
        limit = 30
    ) {
        const domain = [
            ["res_id", "=", res_id],
            ["model", "=", res_model],
            ["message_type", "!=", "user_notification"],
        ];
        const res = this._mockMailMessage_MessageFetch(
            domain,
            search_term,
            before,
            after,
            around,
            limit
        );
        this._mockMailMessageSetMessageDone(res.messages.map((message) => message.id));
        return {
            ...res,
            data: {
                "mail.message": this._mockMailMessageMessageFormat(
                    res.messages.map((message) => message.id)
                ),
            },
            message: res.messages.map((message) => ({ id: message.id })),
        };
    },
});
