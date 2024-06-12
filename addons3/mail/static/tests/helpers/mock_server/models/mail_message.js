/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.model === "mail.message" && args.method === "mark_all_as_read") {
            const domain = args.args[0] || args.kwargs.domain;
            return this._mockMailMessageMarkAllAsRead(domain);
        }
        if (args.model === "mail.message" && args.method === "message_format") {
            const ids = args.args[0];
            return this._mockMailMessageMessageFormat(ids);
        }
        if (args.model === "mail.message" && args.method === "set_message_done") {
            const ids = args.args[0];
            return this._mockMailMessageSetMessageDone(ids);
        }
        if (args.model === "mail.message" && args.method === "toggle_message_starred") {
            const ids = args.args[0];
            return this._mockMailMessageToggleMessageStarred(ids);
        }
        if (args.model === "mail.message" && args.method === "unstar_all") {
            return this._mockMailMessageUnstarAll();
        }
        return super._performRPC(route, args);
    },
    /**
     * Simulates `_bus_notification_target` on `mail.message`.
     *
     * @param {number} messageId
     */
    _mockMailMessage__busNotificationTarget(messageId) {
        const [message] = this.pyEnv["mail.message"].searchRead([["id", "=", messageId]]);
        if (message.model === "discuss.channel") {
            return this.pyEnv["discuss.channel"].searchRead([["id", "=", message.res_id]])[0];
        }
        if (this.pyEnv.currentUser?._is_public()) {
            this._mockMailGuest__getGuestFromContext();
        }
        return this.pyEnv.currentPartner;
    },
    /**
     * Simulates `_message_reaction` on `mail.message`.
     */
    _mockMailMessage_messageReaction(messageId, content, action) {
        const [reaction] = this.pyEnv["mail.message.reaction"].searchRead([
            ["content", "=", content],
            ["message_id", "=", messageId],
            ["partner_id", "=", this.pyEnv.currentPartnerId],
        ]);
        if (action === "add" && !reaction) {
            this.pyEnv["mail.message.reaction"].create({
                content,
                message_id: messageId,
                partner_id: this.pyEnv.currentPartnerId,
            });
        }
        if (action === "remove" && reaction) {
            this.pyEnv["mail.message.reaction"].unlink(reaction.id);
        }
        const reactions = this.pyEnv["mail.message.reaction"].search([
            ["message_id", "=", messageId],
            ["content", "=", content],
        ]);
        const guest = this._mockMailGuest__getGuestFromContext();
        const result = {
            id: messageId,
            reactions: [
                [
                    reactions.length > 0 ? "ADD" : "DELETE",
                    {
                        content,
                        count: reactions.length,
                        message: { id: messageId },
                        personas: [
                            [
                                action === "add" ? "ADD" : "DELETE",
                                {
                                    id: guest ? guest.id : this.pyEnv.currentPartnerId,
                                    name: guest ? guest.name : this.pyEnv.currentPartner.name,
                                    type: guest ? "guest" : "partner",
                                },
                            ],
                        ],
                    },
                ],
            ],
        };
        this.pyEnv["bus.bus"]._sendone(
            this._mockMailMessage__busNotificationTarget(messageId),
            "mail.record/insert",
            { Message: result }
        );
    },
    /**
     * Simulates `mark_all_as_read` on `mail.message`.
     *
     * @private
     * @param {Array[]} [domain]
     * @returns {integer[]}
     */
    _mockMailMessageMarkAllAsRead(domain) {
        const notifDomain = [
            ["res_partner_id", "=", this.pyEnv.currentPartnerId],
            ["is_read", "=", false],
        ];
        if (domain) {
            const messages = this.getRecords("mail.message", domain);
            const ids = messages.map((messages) => messages.id);
            this._mockMailMessageSetMessageDone(ids);
            return ids;
        }
        const notifications = this.getRecords("mail.notification", notifDomain);
        this.pyEnv["mail.notification"].write(
            notifications.map((notification) => notification.id),
            { is_read: true }
        );
        const messageIds = [];
        for (const notification of notifications) {
            if (!messageIds.includes(notification.mail_message_id)) {
                messageIds.push(notification.mail_message_id);
            }
        }
        const messages = this.getRecords("mail.message", [["id", "in", messageIds]]);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.pyEnv["mail.message"].write([message.id], {
                needaction: false,
                needaction_partner_ids: message.needaction_partner_ids.filter(
                    (partnerId) => partnerId !== this.pyEnv.currentPartnerId
                ),
            });
        }
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.message/mark_as_read", {
            message_ids: messageIds,
            needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(
                this.pyEnv.currentPartnerId
            ),
        });
        return messageIds;
    },
    /**
     * Simulates `_message_fetch` on `mail.message`.
     *
     * @private
     * @param {Array[]} domain
     * @param {integer} [before]
     * @param {integer} [after]
     * @param {integer} [limit=30]
     * @returns {Object[]}
     */
    _mockMailMessage_MessageFetch(domain, search_term, before, after, around, limit = 30) {
        const res = {};
        if (search_term) {
            search_term = search_term.replace(" ", "%");
            domain.push(["body", "ilike", search_term]);
            res.count = this.pyEnv["mail.message"].searchCount(domain);
        }
        if (around) {
            const messagesBefore = this.getRecords(
                "mail.message",
                domain.concat([["id", "<=", around]])
            ).sort((m1, m2) => m2.id - m1.id);
            messagesBefore.length = Math.min(messagesBefore.length, limit / 2);
            const messagesAfter = this.getRecords(
                "mail.message",
                domain.concat([["id", ">", around]])
            ).sort((m1, m2) => m1.id - m2.id);
            messagesAfter.length = Math.min(messagesAfter.length, limit / 2);
            return { ...res, messages: messagesAfter.concat(messagesBefore.reverse()) };
        }
        if (before) {
            domain.push(["id", "<", before]);
        }
        if (after) {
            domain.push(["id", ">", after]);
        }
        const messages = this.getRecords("mail.message", domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        // pick at most 'limit' messages
        messages.length = Math.min(messages.length, limit);
        res.messages = messages;
        return res;
    },
    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessageMessageFormat(ids) {
        const messages = this.getRecords("mail.message", [["id", "in", ids]]);
        // sorted from highest ID to lowest ID (i.e. from most to least recent)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        return messages.map((message) => {
            const thread =
                message.model && this.getRecords(message.model, [["id", "=", message.res_id]])[0];
            let author;
            if (message.author_id) {
                const [partner] = this.getRecords("res.partner", [["id", "=", message.author_id]], {
                    active_test: false,
                });
                const [user] = this.getRecords("res.users", [
                    ["partner_id", "=", message.author_id],
                ]);
                author = {
                    id: partner.id,
                    is_company: partner.is_company,
                    name: partner.name,
                    type: "partner",
                };
                if (user) {
                    author["user"] = { id: user.id, isInternalUser: !user.share };
                }
            } else {
                author = false;
            }
            const attachments = this.getRecords("ir.attachment", [
                ["id", "in", message.attachment_ids],
            ]);
            const formattedAttachments = this._mockIrAttachment_attachmentFormat(
                attachments.map((attachment) => attachment.id)
            ).sort((a1, a2) => (a1.id < a2.id ? -1 : 1)); // sort attachments from oldest to most recent
            const allNotifications = this.getRecords("mail.notification", [
                ["mail_message_id", "=", message.id],
            ]);
            const historyPartnerIds = allNotifications
                .filter((notification) => notification.is_read)
                .map((notification) => notification.res_partner_id);
            const needactionPartnerIds = allNotifications
                .filter((notification) => !notification.is_read)
                .map((notification) => notification.res_partner_id);
            let notifications = this._mockMailNotification_FilteredForWebClient(
                allNotifications.map((notification) => notification.id)
            );
            notifications = this._mockMailNotification_NotificationFormat(
                notifications.map((notification) => notification.id)
            );
            const trackingValueIds = this.getRecords("mail.tracking.value", [
                ["id", "in", message.tracking_value_ids],
            ]);
            const formattedTrackingValues =
                this._mockMailTrackingValue_TrackingValueFormat(trackingValueIds);
            const partners = this.getRecords("res.partner", [["id", "in", message.partner_ids]]);
            const linkPreviews = this.getRecords("mail.link.preview", [
                ["id", "in", message.link_preview_ids],
            ]);
            const linkPreviewsFormatted = linkPreviews.map((linkPreview) =>
                this._mockMailLinkPreviewFormat(linkPreview)
            );

            const reactionsPerContent = {};
            for (const reactionId of message.reaction_ids ?? []) {
                const [reaction] = this.getRecords("mail.message.reaction", [
                    ["id", "=", reactionId],
                ]);
                if (reactionsPerContent[reaction.content]) {
                    reactionsPerContent[reaction.content].push(reaction);
                } else {
                    reactionsPerContent[reaction.content] = [reaction];
                }
            }
            const reactionGroups = [];
            for (const content in reactionsPerContent) {
                const reactions = reactionsPerContent[content];
                const guests = reactions
                    .map(
                        (reaction) =>
                            this.getRecords("mail.guest", [["id", "=", reaction.guest_id]])[0]
                    )
                    .filter((guest) => !!guest);
                const partners = reactions
                    .map(
                        (reaction) =>
                            this.getRecords("res.partner", [["id", "=", reaction.partner_id]])[0]
                    )
                    .filter((partner) => !!partner);
                reactionGroups.push({
                    content: content,
                    count: reactionsPerContent[content].length,
                    message: { id: message.id },
                    personas: guests
                        .map((guest) => ({ id: guest.id, name: guest.name, type: "guests" }))
                        .concat(
                            partners.map((partner) => ({
                                id: partner.id,
                                name: partner.name,
                                type: "partner",
                            }))
                        ),
                });
            }
            const response = Object.assign({}, message, {
                attachments: formattedAttachments,
                author,
                history_partner_ids: historyPartnerIds,
                default_subject:
                    message.model &&
                    message.res_id &&
                    this.mockMailThread_MessageComputeSubject(message.model, [message.res_id]).get(
                        message.res_id
                    ),
                linkPreviews: linkPreviewsFormatted,
                reactions: reactionGroups,
                needaction_partner_ids: needactionPartnerIds,
                notifications,
                parentMessage: message.parent_id
                    ? this._mockMailMessageMessageFormat([message.parent_id])[0]
                    : false,
                recipients: partners.map((p) => ({ id: p.id, name: p.name, type: "partner" })),
                record_name:
                    thread && (thread.name !== undefined ? thread.name : thread.display_name),
                trackingValues: formattedTrackingValues,
                pinned_at: message.pinned_at,
            });
            delete response["author_id"];
            if (message.subtype_id) {
                const subtype = this.getRecords("mail.message.subtype", [
                    ["id", "=", message.subtype_id],
                ])[0];
                response.subtype_description = subtype.description;
            }
            let guestAuthor;
            if (message.author_guest_id) {
                const [guest] = this.pyEnv["mail.guest"].searchRead([
                    ["id", "=", message.author_guest_id],
                ]);
                guestAuthor = { id: guest.id, name: guest.name, type: "guest" };
            }
            response.author = author || guestAuthor;
            response["module_icon"] = "/base/static/description/icon.png";
            return response;
        });
    },
    /**
     * Simulate `_message_format_personalize` on `mail.message` for the current partner.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessageFormatPersonalize(ids) {
        const messages = this._mockMailMessageMessageFormat(ids);
        messages.forEach((message) => {
            let user_follower_id = false;
            if (message.model && message.res_id) {
                const follower = this.getRecords("mail.followers", [
                    ["res_model", "=", message.model],
                    ["res_id", "=", message.res_id],
                    ["partner_id", "=", this.pyEnv.currentPartnerId],
                ]);
                if (follower.length !== 0) {
                    user_follower_id = follower[0].id;
                }
            }
            message.user_follower_id = user_follower_id;
        });
        return messages;
    },
    /**
     * Simulates `_message_notification_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessage_MessageNotificationFormat(ids) {
        const messages = this.getRecords("mail.message", [["id", "in", ids]]);
        return messages.map((message) => {
            let notifications = this.getRecords("mail.notification", [
                ["mail_message_id", "=", message.id],
            ]);
            notifications = this._mockMailNotification_FilteredForWebClient(
                notifications.map((notification) => notification.id)
            );
            notifications = this._mockMailNotification_NotificationFormat(
                notifications.map((notification) => notification.id)
            );
            return {
                author: message.author_id ? { id: message.author_id, type: "partner" } : false,
                body: message.body,
                date: message.date,
                id: message.id,
                message_type: message.message_type,
                model: message.model,
                notifications: notifications,
                res_id: message.res_id,
                res_model_name: message.res_model_name,
            };
        });
    },
    /**
     * Simulates `set_message_done` on `mail.message`, which turns provided
     * needaction message to non-needaction (i.e. they are marked as read from
     * from the Inbox mailbox). Also notify on the longpoll bus that the
     * messages have been marked as read, so that UI is updated.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailMessageSetMessageDone(ids) {
        const messages = this.getRecords("mail.message", [["id", "in", ids]]);

        const notifications = this.getRecords("mail.notification", [
            ["res_partner_id", "=", this.pyEnv.currentPartnerId],
            ["is_read", "=", false],
            ["mail_message_id", "in", messages.map((messages) => messages.id)],
        ]);
        if (notifications.length === 0) {
            return;
        }
        this.pyEnv["mail.notification"].write(
            notifications.map((notification) => notification.id),
            { is_read: true }
        );
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.pyEnv["mail.message"].write([message.id], {
                needaction: false,
                needaction_partner_ids: message.needaction_partner_ids.filter(
                    (partnerId) => partnerId !== this.pyEnv.currentPartnerId
                ),
            });
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.message/mark_as_read", {
                message_ids: [message.id],
                needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(
                    this.pyEnv.currentPartnerId
                ),
            });
        }
    },
    /**
     * Simulates `toggle_message_starred` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     */
    _mockMailMessageToggleMessageStarred(ids) {
        const messages = this.getRecords("mail.message", [["id", "in", ids]]);
        for (const message of messages) {
            const wasStared = message.starred_partner_ids.includes(this.pyEnv.currentPartnerId);
            this.pyEnv["mail.message"].write([message.id], {
                starred_partner_ids: [[wasStared ? 3 : 4, this.pyEnv.currentPartnerId]],
            });
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.message/toggle_star", {
                message_ids: [message.id],
                starred: !wasStared,
            });
        }
    },
    /**
     * Simulates `unstar_all` on `mail.message`.
     *
     * @private
     */
    _mockMailMessageUnstarAll() {
        const messages = this.getRecords("mail.message", [
            ["starred_partner_ids", "in", this.pyEnv.currentPartnerId],
        ]);
        this.pyEnv["mail.message"].write(
            messages.map((message) => message.id),
            { starred_partner_ids: [[3, this.pyEnv.currentPartnerId]] }
        );
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.message/toggle_star", {
            message_ids: messages.map((message) => message.id),
            starred: false,
        });
    },
});
