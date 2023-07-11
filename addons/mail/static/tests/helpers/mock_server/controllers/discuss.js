/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/controllers/discuss", {
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
            const attachment = this.getRecords("ir.attachment", [["id", "=", attachmentId]])[0];
            return {
                filename: attachment.name,
                name: attachment.name,
                id: attachment.id,
                mimetype: attachment.mimetype,
                size: attachment.file_size,
            };
        }
        return this._super(...arguments);
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
            const { channel_id, after, around, before, limit } = args;
            return this._mockRouteDiscussChannelMessages(channel_id, before, after, around, limit);
        }
        if (route === "/discuss/channel/pinned_messages") {
            const { channel_id } = args;
            return this._mockRouteDiscussChannelPins(channel_id);
        }
        if (route === "/discuss/channel/notify_typing") {
            const id = args.channel_id;
            const is_typing = args.is_typing;
            const context = args.context;
            return this._mockRouteDiscussChannelNotifyTyping(id, is_typing, context);
        }
        if (new RegExp("/discuss/channel/\\d+/partner/\\d+/avatar_128").test(route)) {
            return;
        }
        if (route === "/discuss/channel/ping") {
            return;
        }
        if (route === "/discuss/channel/members") {
            const { channel_id, known_member_ids } = args;
            return this._mockDiscussChannelloadOlderMembers([channel_id], known_member_ids);
        }
        if (route === "/mail/history/messages") {
            const { after, before, limit } = args;
            return this._mockRouteMailMessageHistory(after, before, limit);
        }
        if (route === "/mail/init_messaging") {
            return this._mockRouteMailInitMessaging();
        }
        if (route === "/mail/inbox/messages") {
            const { after, around, before, limit } = args;
            return this._mockRouteMailMessageInbox(after, before, around, limit);
        }
        if (route === "/mail/link_preview") {
            return this._mockRouteMailLinkPreview(args.message_id, args.clear);
        }
        if (route == "/mail/link_preview/delete") {
            const [linkPreview] = this.pyEnv["mail.link.preview"].searchRead([
                ["id", "=", args.link_preview_id],
            ]);
            this.pyEnv["bus.bus"]._sendone(
                this.pyEnv.currentPartnerId,
                "mail.link.preview/delete",
                {
                    id: linkPreview.id,
                    message_id: linkPreview.message_id[0],
                }
            );
            return args;
        }
        if (route === "/mail/load_message_failures") {
            return this._mockRouteMailLoadMessageFailures();
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
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartnerId, "mail.record/insert", {
                Message: {
                    id: args.message_id,
                    body: args.body,
                    attachment_ids: this._mockIrAttachment_attachmentFormat(args.attachment_ids),
                },
            });
            return this._mockMailMessageMessageFormat([args.message_id])[0];
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
            return;
        }
        if (route === "/mail/starred/messages") {
            const { after, before, limit } = args;
            return this._mockRouteMailMessageStarredMessages(after, before, limit);
        }
        if (route === "/mail/thread/data") {
            return this._mockRouteMailThreadData(
                args.thread_model,
                args.thread_id,
                args.request_list
            );
        }
        if (route === "/mail/thread/messages") {
            const { after, around, before, limit, thread_model, thread_id } = args;
            return this._mockRouteMailThreadFetchMessages(
                thread_model,
                thread_id,
                before,
                after,
                around,
                limit
            );
        }
        if (route === "/discuss/gif/favorites") {
            return [[]];
        }
        return this._super(route, args);
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
        return this._mockMailMessageMessageFormat(messageIds);
    },
    /**
     * Simulates the `/mail/init_messaging` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailInitMessaging() {
        return this._mockResUsers_InitMessaging([this.currentUserId]);
    },
    /**
     * Simulates the `/mail/attachment/delete` route.
     *
     * @private
     * @param {integer} attachment_id
     */
    async _mockRouteMailAttachmentRemove(attachment_id) {
        this.pyEnv["bus.bus"]._sendone(this.currentPartnerId, "ir.attachment/delete", {
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
        const messages = this._mockMailMessage_MessageFetch(domain, before, after, around, limit);
        if (!around) {
            this._mockMailMessageSetMessageDone(messages.map((message) => message.id));
        }
        return this._mockMailMessageMessageFormat(messages.map((message) => message.id));
    },
    /**
     * Simulates the `/discuss/channel/notify_typing` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} limit
     * @param {Object} [context={}]
     */
    async _mockRouteDiscussChannelNotifyTyping(channel_id, is_typing, context = {}) {
        const partnerId = context.mockedPartnerId || this.currentPartnerId;
        const [memberOfCurrentUser] = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", channel_id],
            ["partner_id", "=", partnerId],
        ]);
        if (!memberOfCurrentUser) {
            return;
        }
        this._mockDiscussChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
    /**
     * Simulates the `/mail/load_message_failures` route.
     *
     * @private
     * @returns {Object[]}
     */
    _mockRouteMailLoadMessageFailures() {
        return this._mockResPartner_MessageFetchFailed(this.currentPartnerId);
    },
    /**
     * Simulates `/mail/link_preview` route.
     *
     * @private
     * @param {integer} message_id
     * @returns {Object}
     */
    _mockRouteMailLinkPreview(message_id, clear = false) {
        const linkPreviews = [];
        const [message] = this.pyEnv["mail.message"].searchRead([["id", "=", message_id]]);
        if (message.body === "https://make-link-preview.com") {
            if (clear) {
                const [linkPreview] = this.pyEnv["mail.link.preview"].searchRead([
                    ["message_id", "=", message_id],
                ]);
                this.pyEnv["bus.bus"]._sendone(
                    this.pyEnv.currentPartnerId,
                    "mail.link.preview/delete",
                    {
                        id: linkPreview.id,
                        message_id: linkPreview.message_id[0],
                    }
                );
            }

            const linkPreviewId = this.pyEnv["mail.link.preview"].create({
                og_description: "test description",
                og_title: "Article title",
                og_type: "article",
                source_url: "https://make-link-preview.com",
            });
            const [linkPreview] = this.pyEnv["mail.link.preview"].searchRead([
                ["id", "=", linkPreviewId],
            ]);
            linkPreviews.push(this._mockMailLinkPreviewFormat(linkPreview));
            let target = this.pyEnv.currentPartner;
            if (message.model === "discuss.channel") {
                target = this.pyEnv["discuss.channel"].search([["id", "=", message.res_id]]);
            }
            this.pyEnv["bus.bus"]._sendmany([
                [target, "mail.record/insert", { LinkPreview: linkPreviews }],
            ]);
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
    _mockRouteMailMessageHistory(after = false, before = false, limit = 30) {
        const domain = [["needaction", "=", false]];
        const messages = this._mockMailMessage_MessageFetch(domain, before, after, false, limit);
        const messagesWithNotification = messages.filter((message) => {
            const notifs = this.pyEnv["mail.notification"].searchRead([
                ["mail_message_id", "=", message.id],
                ["is_read", "=", true],
                ["res_partner_id", "=", this.currentPartnerId],
            ]);
            return notifs.length > 0;
        });

        return this._mockMailMessageMessageFormat(
            messagesWithNotification.map((message) => message.id)
        );
    },
    /**
     * Simulates the `/mail/inbox/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageInbox(after = false, before = false, around = false, limit = 30) {
        const domain = [["needaction", "=", true]];
        const messages = this._mockMailMessage_MessageFetch(domain, before, after, around, limit);
        return this._mockMailMessageFormatPersonalize(messages.map((message) => message.id));
    },
    /**
     * Simulates the `/mail/starred/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageStarredMessages(after = false, before = false, limit = 30) {
        const domain = [["starred_partner_ids", "in", [this.currentPartnerId]]];
        const messages = this._mockMailMessage_MessageFetch(domain, before, after, false, limit);
        return this._mockMailMessageMessageFormat(messages.map((message) => message.id));
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
        const [currentChannelMember] = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", channel_id],
            ["partner_id", "=", this.currentPartnerId],
        ]);
        const sessionId = this.pyEnv["discuss.channel.rtc.session"].create({
            channel_member_id: currentChannelMember.id,
            channel_id, // on the server, this is a related field from channel_member_id and not explicitly set
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
                    "insert",
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
            const notificationRtcSessions = sessionsData.map((sessionsDataPoint) => {
                return { id: sessionsDataPoint.id };
            });
            notifications.push([
                channelId,
                "discuss.channel/rtc_sessions_update",
                {
                    id: Number(channelId), // JS object keys are strings, but the type from the server is number
                    rtcSessions: [["insert-and-unlink", notificationRtcSessions]],
                },
            ]);
        }
        for (const rtcSession of rtcSessions) {
            const target = rtcSession.guest_id || rtcSession.partner_id;
            notifications.push([
                target,
                "discuss.channel.rtc.session/ended",
                { sessionId: rtcSession.id },
            ]);
        }
        this.pyEnv["bus.bus"]._sendmany(notifications);
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
        };
        const thread = this.pyEnv[thread_model].searchRead([["id", "=", thread_id]])[0];
        if (!thread) {
            res["hasReadAccess"] = false;
            return res;
        }
        res["canPostOnReadonly"] = thread_model === "discuss.channel"; // model that have attr _mail_post_access='read'
        if (request_list.includes("activities")) {
            const activities = this.pyEnv["mail.activity"].searchRead([
                ["id", "in", thread.activity_ids || []],
            ]);
            res["activities"] = this._mockMailActivityActivityFormat(
                activities.map((activity) => activity.id)
            );
        }
        if (request_list.includes("attachments")) {
            const attachments = this.pyEnv["ir.attachment"].searchRead([
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
                    : [["clear"]];
            }
        }
        if (request_list.includes("followers")) {
            const followers = this.pyEnv["mail.followers"].searchRead([
                ["id", "in", thread.message_follower_ids || []],
            ]);
            // search read returns many2one relations as an array [id, display_name].
            // But the original route does not. Thus, we need to change it now.
            followers.forEach((follower) => {
                follower.partner_id = follower.partner_id[0];
                follower.partner = this._mockResPartnerMailPartnerFormat([follower.partner_id]).get(
                    follower.partner_id
                );
            });
            res["followers"] = followers;
        }
        if (request_list.includes("suggestedRecipients")) {
            res["suggestedRecipients"] = this._mockMailThread_MessageGetSuggestedRecipients(
                thread_model,
                [thread.id]
            )[thread_id];
        }
        return res;
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
        const messages = this._mockMailMessage_MessageFetch(domain, before, after, around, limit);
        this._mockMailMessageSetMessageDone(messages.map((message) => message.id));
        return this._mockMailMessageMessageFormat(messages.map((message) => message.id));
    },
});
