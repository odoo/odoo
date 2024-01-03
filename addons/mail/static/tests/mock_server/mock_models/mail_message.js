/** @odoo-module */

import { Command, fields, models } from "@web/../tests/web_test_helpers";

/**
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 */

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

export class MailMessage extends models.ServerModel {
    _name = "mail.message";

    author_id = fields.Generic({ default: () => this.env.partner_id });
    history_partner_ids = fields.Many2many({
        relation: "res.partner",
        string: "Partners with History",
    });
    is_discussion = fields.Boolean({ string: "Discussion" });
    is_note = fields.Boolean({ string: "Note" });
    needaction_partner_ids = fields.Many2many({
        relation: "res.partner",
        string: "Partners with Need Action",
    });
    pinned_at = fields.Generic({ default: false });
    res_model_name = fields.Char({ string: "Res Model Name" });

    /**
     * Simulates `mark_all_as_read` on `mail.message`.
     *
     * @param {DomainListRepr} [domain]
     * @param {KwArgs<{ domain: DomainListRepr }>} [kwargs]
     */
    mark_all_as_read(domain, kwargs = {}) {
        domain = kwargs.domain || domain || [];
        const notifDomain = [
            ["res_partner_id", "=", this.env.partner_id],
            ["is_read", "=", false],
        ];
        if (domain) {
            const messages = this._filter(domain);
            const ids = messages.map((messages) => messages.id);
            this.set_message_done(ids);
            return ids;
        }
        const notifications = this.env["mail.notification"]._filter(notifDomain);
        this.env["mail.notification"].write(
            notifications.map((notification) => notification.id),
            { is_read: true }
        );
        const messageIds = [];
        for (const notification of notifications) {
            if (!messageIds.includes(notification.mail_message_id)) {
                messageIds.push(notification.mail_message_id);
            }
        }
        const messages = this._filter([["id", "in", messageIds]]);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.write([message.id], {
                needaction: false,
                needaction_partner_ids: message.needaction_partner_ids.filter(
                    (partnerId) => partnerId !== this.env.partner_id
                ),
            });
        }
        this.env["bus.bus"]._sendone(this.env.partner, "mail.message/mark_as_read", {
            message_ids: messageIds,
            needaction_inbox_counter: this.env["res.partner"]._getNeedactionCount(
                this.env.partner_id
            ),
        });
        return messageIds;
    }

    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @param {number[]} ids
     * @param {KwArgs} [kwargs]
     */
    message_format(ids, kwargs = {}) {
        const messages = this._filter([["id", "in", ids]]);
        // sorted from highest ID to lowest ID (i.e. from most to least recent)
        messages.sort((m1, m2) => (m1.id < m2.id ? 1 : -1));
        const Attachment = this.env["ir.attachment"];
        const Notification = this.env["mail.notification"];
        return messages.map((message) => {
            const thread =
                message.model && this.env[message.model]._filter([["id", "=", message.res_id]])[0];
            let author;
            if (message.author_id) {
                const [partner] = this.env["res.partner"]._filter(
                    [["id", "=", message.author_id]],
                    { active_test: false }
                );
                const [user] = this.env["res.users"]._filter([
                    ["partner_id", "=", message.author_id],
                ]);
                author = this.env["res.partner"].mail_partner_format([partner.id])[partner.id];
                if (user) {
                    author["user"] = { id: user.id, isInternalUser: !user.share };
                }
            } else {
                author = false;
            }
            const attachments = Attachment._filter([["id", "in", message.attachment_ids]]);
            const formattedAttachments = Attachment._attachmentFormat(
                attachments.map((attachment) => attachment.id)
            ).sort((a1, a2) => (a1.id < a2.id ? -1 : 1)); // sort attachments from oldest to most recent
            const allNotifications = Notification._filter([["mail_message_id", "=", message.id]]);
            const historyPartnerIds = allNotifications
                .filter((notification) => notification.is_read)
                .map((notification) => notification.res_partner_id);
            const needactionPartnerIds = allNotifications
                .filter((notification) => !notification.is_read)
                .map((notification) => notification.res_partner_id);
            let notifications = Notification._filteredForWebClient(
                allNotifications.map((notification) => notification.id)
            );
            notifications = Notification._notificationFormat(
                notifications.map((notification) => notification.id)
            );
            const trackingValues = this.env["mail.tracking.value"]._filter([
                ["id", "in", message.tracking_value_ids],
            ]);
            const formattedTrackingValues =
                this.env["mail.tracking.value"]._trackingValueFormat(trackingValues);
            const partners = this.env["res.partner"]._filter([["id", "in", message.partner_ids]]);
            const linkPreviews = this.env["mail.link.preview"]._filter([
                ["id", "in", message.link_preview_ids],
            ]);
            const linkPreviewsFormatted = linkPreviews.map((linkPreview) =>
                this.env["mail.link"]._linkPreviewFormat(linkPreview)
            );

            const reactionsPerContent = {};
            for (const reactionId of message.reaction_ids ?? []) {
                const [reaction] = this.env["mail.message.reaction"]._filter([
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
                            this.env["mail.guest"]._filter([["id", "=", reaction.guest_id]])[0]
                    )
                    .filter((guest) => !!guest);
                const partners = reactions
                    .map(
                        (reaction) =>
                            this.env["res.partner"]._filter([["id", "=", reaction.partner_id]])[0]
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
            const response = {
                ...message,
                attachments: formattedAttachments,
                author,
                history_partner_ids: historyPartnerIds,
                default_subject:
                    message.model &&
                    message.res_id &&
                    this.env["mail.thread"]
                        ._messageComputeSubject(message.model, [message.res_id])
                        .get(message.res_id),
                linkPreviews: linkPreviewsFormatted,
                reactions: reactionGroups,
                needaction_partner_ids: needactionPartnerIds,
                notifications,
                parentMessage: message.parent_id
                    ? this.message_format([message.parent_id])[0]
                    : false,
                recipients: partners.map((p) => ({ id: p.id, name: p.name, type: "partner" })),
                record_name:
                    thread && (thread.name !== undefined ? thread.name : thread.display_name),
                starredPersonas: message.starred_partner_ids.map((id) => ({ id, type: "partner" })),
                trackingValues: formattedTrackingValues,
                pinned_at: message.pinned_at,
            };
            delete response.author_id;
            if (message.subtype_id) {
                const subtype = this.env["mail.message.subtype"]._filter([
                    ["id", "=", message.subtype_id],
                ])[0];
                response.subtype_description = subtype.description;
            }
            let guestAuthor;
            if (message.author_guest_id) {
                const [guest] = this.env["mail.guest"].search_read([
                    ["id", "=", message.author_guest_id],
                ]);
                guestAuthor = { id: guest.id, name: guest.name, type: "guest" };
            }
            response.author = author || guestAuthor;
            if (response.model && response.res_id) {
                const originThread = {
                    model: response.model,
                    id: response.res_id,
                    module_icon: "/base/static/description/icon.png",
                };
                if (response.model !== "discuss.channel") {
                    originThread.name = response.record_name;
                }
                Object.assign(response, { originThread });
            }
            return response;
        });
    }

    /**
     * Simulates `set_message_done` on `mail.message`, which turns provided
     * needaction message to non-needaction (i.e. they are marked as read from
     * from the Inbox mailbox). Also notify on the longpoll bus that the
     * messages have been marked as read, so that UI is updated.
     *
     * @param {number[]} ids
     * @param {KwArgs} [kwargs]
     */
    set_message_done(ids, kwargs = {}) {
        const messages = this._filter([["id", "in", ids]]);

        const notifications = this.env["mail.notification"]._filter([
            ["res_partner_id", "=", this.env.partner_id],
            ["is_read", "=", false],
            ["mail_message_id", "in", messages.map((messages) => messages.id)],
        ]);
        if (notifications.length === 0) {
            return;
        }
        this.env["mail.notification"].write(
            notifications.map((notification) => notification.id),
            { is_read: true }
        );
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.write([message.id], {
                needaction: false,
                needaction_partner_ids: message.needaction_partner_ids.filter(
                    (partnerId) => partnerId !== this.env.partner_id
                ),
            });
            this.env["bus.bus"]._sendone(this.env.partner, "mail.message/mark_as_read", {
                message_ids: [message.id],
                needaction_inbox_counter: this.env["res.partner"]._getNeedactionCount(
                    this.env.partner_id
                ),
            });
        }
    }

    /**
     * Simulates `toggle_message_starred` on `mail.message`.
     *
     * @param {number[]} ids
     * @param {KwArgs} [kwargs]
     */
    toggle_message_starred(ids, kwargs = {}) {
        const messages = this._filter([["id", "in", ids]]);
        for (const message of messages) {
            const wasStared = message.starred_partner_ids.includes(this.env.partner_id);
            this.write([message.id], {
                starred_partner_ids: [[wasStared ? 3 : 4, this.env.partner_id]],
            });
            this.env["bus.bus"]._sendone(this.env.partner, "mail.message/toggle_star", {
                message_ids: [message.id],
                starred: !wasStared,
            });
        }
    }

    /**
     * Simulates `unstar_all` on `mail.message`.
     *
     * @param {KwArgs} [kwargs]
     */
    unstar_all(kwargs = {}) {
        const messages = this._filter([["starred_partner_ids", "in", this.env.partner_id]]);
        this.write(
            messages.map((message) => message.id),
            { starred_partner_ids: [Command.unlink(this.env.partner_id)] }
        );
        this.env["bus.bus"]._sendone(this.env.partner, "mail.message/toggle_star", {
            message_ids: messages.map((message) => message.id),
            starred: false,
        });
    }

    /**
     * Simulates `_bus_notification_target` on `mail.message`.
     *
     * @param {number} messageId
     */
    _busNotificationTarget(messageId) {
        const [message] = this.search_read([["id", "=", messageId]]);
        if (message.model === "discuss.channel") {
            return this.env["discuss.channel"].search_read([["id", "=", message.res_id]])[0];
        }
        if (this.env.user?.is_public) {
            this.env["mail.guest"]._getGuestFromContext();
        }
        return this.env.partner;
    }

    /**
     * Simulates `_message_reaction` on `mail.message`.
     *
     * @param {number} messageId
     * @param {string} content
     * @param {string} action
     */
    _messageReaction(messageId, content, action) {
        const [reaction] = this.env["mail.message.reaction"].search_read([
            ["content", "=", content],
            ["message_id", "=", messageId],
            ["partner_id", "=", this.env.partner_id],
        ]);
        if (action === "add" && !reaction) {
            this.env["mail.message.reaction"].create({
                content,
                message_id: messageId,
                partner_id: this.env.partner_id,
            });
        }
        if (action === "remove" && reaction) {
            this.env["mail.message.reaction"].unlink(reaction.id);
        }
        const reactions = this.env["mail.message.reaction"].search([
            ["message_id", "=", messageId],
            ["content", "=", content],
        ]);
        const guest = this.env["mail.guest"]._getGuestFromContext();
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
                                    id: guest ? guest.id : this.env.partner_id,
                                    name: guest ? guest.name : this.env.partner.name,
                                    type: guest ? "guest" : "partner",
                                },
                            ],
                        ],
                    },
                ],
            ],
        };
        this.env["bus.bus"]._sendone(this._busNotificationTarget(messageId), "mail.record/insert", {
            Message: result,
        });
    }

    /**
     * Simulates `_message_fetch` on `mail.message`.
     *
     * @param {DomainListRepr} domain
     * @param {number} [before]
     * @param {number} [after]
     * @param {number} [limit=30]
     * @returns {Object[]}
     */
    _messageFetch(domain, search_term, before, after, around, limit = 30) {
        const res = {};
        if (search_term) {
            search_term = search_term.replace(" ", "%");
            domain.push(["body", "ilike", search_term]);
            res.count = this.search_count(domain);
        }
        if (around) {
            const messagesBefore = this._filter(domain.concat([["id", "<=", around]])).sort(
                (m1, m2) => m2.id - m1.id
            );
            messagesBefore.length = Math.min(messagesBefore.length, limit / 2);
            const messagesAfter = this._filter(domain.concat([["id", ">", around]])).sort(
                (m1, m2) => m1.id - m2.id
            );
            messagesAfter.length = Math.min(messagesAfter.length, limit / 2);
            return { ...res, messages: messagesAfter.concat(messagesBefore.reverse()) };
        }
        if (before) {
            domain.push(["id", "<", before]);
        }
        if (after) {
            domain.push(["id", ">", after]);
        }
        const messages = this._filter(domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        // pick at most 'limit' messages
        messages.length = Math.min(messages.length, limit);
        res.messages = messages;
        return res;
    }

    /**
     * Simulate `_message_format_personalize` on `mail.message` for the current partner.
     *
     * @param {number[]} ids
     */
    _messageFormatPersonalize(ids) {
        const messages = this.message_format(ids);
        messages.forEach((message) => {
            if (message.model && message.res_id) {
                const follower = this.env["mail.followers"]._filter([
                    ["res_model", "=", message.model],
                    ["res_id", "=", message.res_id],
                    ["partner_id", "=", this.env.partner_id],
                ]);
                if (follower.length !== 0) {
                    message.originThread.selfFollower = {
                        id: follower[0].id,
                        is_active: true,
                        partner: { id: this.env.partner_id, type: "partner" },
                    };
                }
            }
        });
        return messages;
    }

    /**
     * Simulates `_message_notification_format` on `mail.message`.
     *
     * @returns {number[]} ids
     * @returns {Object[]}
     */
    _messageNotificationFormat(ids) {
        const messages = this._filter([["id", "in", ids]]);
        return messages.map((message) => {
            const Notification = this.env["mail.notification"];
            let notifications = Notification._filter([["mail_message_id", "=", message.id]]);
            notifications = Notification._filteredForWebClient(
                notifications.map((notification) => notification.id)
            );
            notifications = Notification._notificationFormat(
                notifications.map((notification) => notification.id)
            );
            return {
                author: message.author_id ? { id: message.author_id, type: "partner" } : false,
                body: message.body,
                date: message.date,
                id: message.id,
                message_type: message.message_type,
                notifications: notifications,
                originThread: message.res_id
                    ? {
                          id: message.res_id,
                          model: message.model,
                          modelName: message.res_model_name,
                      }
                    : false,
            };
        });
    }
}
