import { Command, fields, models, serverState } from "@web/../tests/web_test_helpers";
import { parseModelParams } from "../mail_mock_server";

/** @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr */

export class MailMessage extends models.ServerModel {
    _name = "mail.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });
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

    /** @param {DomainListRepr} [domain] */
    mark_all_as_read(domain) {
        const kwargs = parseModelParams(arguments, "domain");
        domain = kwargs.domain || [];

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const notifDomain = [
            ["res_partner_id", "=", this.env.user.partner_id],
            ["is_read", "=", false],
        ];
        if (domain) {
            const messages = this._filter(domain);
            const ids = messages.map((messages) => messages.id);
            this.set_message_done(ids);
            return ids;
        }
        const notifications = MailNotification._filter(notifDomain);
        MailNotification.write(
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
                    (partnerId) => partnerId !== this.env.user.partner_id
                ),
            });
        }
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "mail.message/mark_as_read", {
            message_ids: messageIds,
            needaction_inbox_counter: ResPartner._get_needaction_count(this.env.user.partner_id),
        });
        return messageIds;
    }

    /** @param {number[]} ids */
    _message_format(ids) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailLinkPreview} */
        const MailLinkPreview = this.env["mail.link.preview"];
        /** @type {import("mock_models").MailMessageReaction} */
        const MailMessageReaction = this.env["mail.message.reaction"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").MailTrackingValue} */
        const MailTrackingValue = this.env["mail.tracking.value"];
        /** @type {import("mock_models").ResFake} */
        const ResFake = this.env["res.fake"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const messages = this._filter([["id", "in", ids]]);
        // sorted from highest ID to lowest ID (i.e. from most to least recent)
        messages.sort((m1, m2) => (m1.id < m2.id ? 1 : -1));
        return messages.map((message) => {
            const thread =
                message.model && this.env[message.model]._filter([["id", "=", message.res_id]])[0];
            let author;
            if (message.author_id) {
                const [partner] = ResPartner._filter([["id", "=", message.author_id]], {
                    active_test: false,
                });
                author = ResPartner.mail_partner_format([partner.id])[partner.id];
            } else {
                author = false;
            }
            const attachments = IrAttachment._filter([["id", "in", message.attachment_ids]]);
            const formattedAttachments = IrAttachment._attachment_format(
                attachments.map((attachment) => attachment.id)
            ).sort((a1, a2) => (a1.id < a2.id ? -1 : 1)); // sort attachments from oldest to most recent
            const allNotifications = MailNotification._filter([
                ["mail_message_id", "=", message.id],
            ]);
            const historyPartnerIds = allNotifications
                .filter((notification) => notification.is_read)
                .map((notification) => notification.res_partner_id);
            const needactionPartnerIds = allNotifications
                .filter((notification) => !notification.is_read)
                .map((notification) => notification.res_partner_id);
            let notifications = MailNotification._filtered_for_web_client(
                allNotifications.map((notification) => notification.id)
            );
            notifications = MailNotification._notification_format(
                notifications.map((notification) => notification.id)
            );
            const trackingValues = MailTrackingValue._filter([
                ["id", "in", message.tracking_value_ids],
            ]);
            const formattedTrackingValues =
                MailTrackingValue._tracking_value_format(trackingValues);
            const partners = ResPartner._filter([["id", "in", message.partner_ids]]);
            const linkPreviews = MailLinkPreview._filter([["id", "in", message.link_preview_ids]]);
            const linkPreviewsFormatted = linkPreviews.map((linkPreview) =>
                MailLinkPreview._link_preview_format(linkPreview)
            );
            const reactionsPerContent = {};
            for (const reactionId of message.reaction_ids ?? []) {
                const [reaction] = MailMessageReaction._filter([["id", "=", reactionId]]);
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
                    .map((reaction) => MailGuest._filter([["id", "=", reaction.guest_id]])[0])
                    .filter((guest) => !!guest);
                const partners = reactions
                    .map((reaction) => ResPartner._filter([["id", "=", reaction.partner_id]])[0])
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
                    (message.model === "res.fake"
                        ? ResFake._message_compute_subject([message.res_id])
                        : MailThread._message_compute_subject([message.res_id])
                    ).get(message.res_id),
                linkPreviews: linkPreviewsFormatted,
                reactions: reactionGroups,
                needaction_partner_ids: needactionPartnerIds,
                notifications,
                parentMessage: message.parent_id
                    ? this._message_format([message.parent_id])[0]
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
                const subtype = MailMessageSubtype._filter([["id", "=", message.subtype_id]])[0];
                response.subtype_description = subtype.description;
            }
            let guestAuthor;
            if (message.author_guest_id) {
                const [guest] = MailGuest.search_read([["id", "=", message.author_guest_id]]);
                guestAuthor = { id: guest.id, name: guest.name, type: "guest" };
            }
            response.author = author || guestAuthor;
            if (response.model && response.res_id) {
                const thread = {
                    model: response.model,
                    id: response.res_id,
                    module_icon: "/base/static/description/icon.png",
                };
                if (response.model !== "discuss.channel") {
                    thread.name = response.record_name;
                }
                Object.assign(response, { thread });
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
     */
    set_message_done(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (!this.env.user) {
            return;
        }
        const messages = this._filter([["id", "in", ids]]);
        const notifications = MailNotification._filter([
            ["res_partner_id", "=", this.env.user.partner_id],
            ["is_read", "=", false],
            ["mail_message_id", "in", messages.map((messages) => messages.id)],
        ]);
        if (notifications.length === 0) {
            return;
        }
        MailNotification.write(
            notifications.map((notification) => notification.id),
            { is_read: true }
        );
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.write([message.id], {
                needaction: false,
                needaction_partner_ids: message.needaction_partner_ids.filter(
                    (partnerId) => partnerId !== this.env.user.partner_id
                ),
            });
            const [partner] = ResPartner.read(this.env.user.partner_id);
            BusBus._sendone(partner, "mail.message/mark_as_read", {
                message_ids: [message.id],
                needaction_inbox_counter: ResPartner._get_needaction_count(
                    this.env.user.partner_id
                ),
            });
        }
    }

    /** @param {number[]} ids */
    toggle_message_starred(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const messages = this._filter([["id", "in", ids]]);
        for (const message of messages) {
            const wasStarred = message.starred_partner_ids.includes(this.env.user.partner_id);
            this.write([message.id], {
                starred_partner_ids: [
                    wasStarred
                        ? Command.unlink(this.env.user.partner_id)
                        : Command.link(this.env.user.partner_id),
                ],
            });
            const [partner] = ResPartner.read(this.env.user.partner_id);
            BusBus._sendone(partner, "mail.message/toggle_star", {
                message_ids: [message.id],
                starred: !wasStarred,
            });
        }
    }

    unstar_all() {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const messages = this._filter([["starred_partner_ids", "in", this.env.user.partner_id]]);
        this.write(
            messages.map((message) => message.id),
            { starred_partner_ids: [Command.unlink(this.env.user.partner_id)] }
        );
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "mail.message/toggle_star", {
            message_ids: messages.map((message) => message.id),
            starred: false,
        });
    }

    /** @param {number} id */
    _bus_notification_target(id) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const [message] = this.search_read([["id", "=", id]]);
        if (message.model === "discuss.channel") {
            return DiscussChannel.search_read([["id", "=", message.res_id]])[0];
        }
        if (ResUsers._is_public(this.env.uid)) {
            MailGuest._get_guest_from_context();
        }
        return ResPartner.read(this.env.user.partner_id)[0];
    }

    /**
     * @param {number} id
     * @param {string} content
     * @param {string} action
     */
    _message_reaction(id, content, action) {
        const kwargs = parseModelParams(arguments, "id", "content", "action");
        id = kwargs.id;
        delete kwargs.id;
        content = kwargs.content;
        action = kwargs.action;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessageReaction} */
        const MailMessageReaction = this.env["mail.message.reaction"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const partner_id = this.env.user?.partner_id ?? false;
        const guest_id = this.env.cookie.get("dgid") ?? false;
        const [reaction] = MailMessageReaction.search_read([
            ["content", "=", content],
            ["message_id", "=", id],
            ["partner_id", "=", partner_id],
            ["guest_id", "=", guest_id],
        ]);
        if (action === "add" && !reaction) {
            MailMessageReaction.create({
                content,
                message_id: id,
                partner_id,
                guest_id,
            });
        }
        if (action === "remove" && reaction) {
            MailMessageReaction.unlink(reaction.id);
        }
        const reactions = MailMessageReaction.search([
            ["message_id", "=", id],
            ["content", "=", content],
        ]);
        const guest = MailGuest._get_guest_from_context();
        const [partner] = ResPartner.read(serverState.partnerId);
        const result = {
            id,
            reactions: [
                [
                    reactions.length > 0 ? "ADD" : "DELETE",
                    {
                        content,
                        count: reactions.length,
                        message: { id },
                        personas: [
                            [
                                action === "add" ? "ADD" : "DELETE",
                                {
                                    id: guest ? guest.id : partner.id,
                                    name: guest ? guest.name : partner.name,
                                    type: guest ? "guest" : "partner",
                                },
                            ],
                        ],
                    },
                ],
            ],
        };
        BusBus._sendone(this._bus_notification_target(id), "mail.record/insert", {
            Message: result,
        });
    }

    /**
     * @param {DomainListRepr} domain
     * @param {number} [before]
     * @param {number} [after]
     * @param {number} [limit=30]
     * @returns {Object[]}
     */
    _message_fetch(domain, search_term, before, after, around, limit) {
        const kwargs = parseModelParams(
            arguments,
            "domain",
            "search_term",
            "before",
            "after",
            "around",
            "limit"
        );
        domain = kwargs.domain;
        search_term = kwargs.search_term;
        before = kwargs.before;
        after = kwargs.after;
        around = kwargs.around;
        limit = kwargs.limit || 30;

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

    /** @param {number[]} ids */
    _message_format_personalize(ids) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        const messages = this._message_format(ids);
        messages.forEach((message) => {
            if (message.model && message.res_id) {
                const follower = MailFollowers._filter([
                    ["res_model", "=", message.model],
                    ["res_id", "=", message.res_id],
                    ["partner_id", "=", this.env.user.partner_id],
                ]);
                if (follower.length !== 0) {
                    message.thread.selfFollower = {
                        id: follower[0].id,
                        is_active: true,
                        partner: { id: this.env.user.partner_id, type: "partner" },
                    };
                }
            }
        });
        return messages;
    }

    /**
     * @returns {number[]} ids
     * @returns {Object[]}
     */
    _message_notification_format(ids) {
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        const messages = this._filter([["id", "in", ids]]);
        return messages.map((message) => {
            let notifications = MailNotification._filter([["mail_message_id", "=", message.id]]);
            notifications = MailNotification._filtered_for_web_client(
                notifications.map((notification) => notification.id)
            );
            notifications = MailNotification._notification_format(
                notifications.map((notification) => notification.id)
            );
            return {
                author: message.author_id ? { id: message.author_id, type: "partner" } : false,
                body: message.body,
                date: message.date,
                id: message.id,
                message_type: message.message_type,
                notifications: notifications,
                thread: message.res_id
                    ? {
                          id: message.res_id,
                          model: message.model,
                          modelName: this.env[message.model]._description,
                      }
                    : false,
            };
        });
    }
}
