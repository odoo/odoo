import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import {
    Command,
    fields,
    getKwArgs,
    makeKwArgs,
    models,
    serverState,
} from "@web/../tests/web_test_helpers";

/** @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr */

export class MailMessage extends models.ServerModel {
    _name = "mail.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });
    is_discussion = fields.Boolean({ string: "Discussion" });
    is_note = fields.Boolean({ string: "Note" });
    pinned_at = fields.Generic({ default: false });

    /** @param {DomainListRepr} [domain] */
    mark_all_as_read(domain) {
        ({ domain } = getKwArgs(arguments, "domain"));

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
        const messages = this.browse(messageIds);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.write([message.id], {
                needaction: false,
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
    _to_store(ids, store, fields, for_current_user, add_followers) {
        const kwargs = getKwArgs(arguments, "ids", "store", "for_current_user", "add_followers");
        ids = kwargs.ids;
        store = kwargs.store;
        fields = kwargs.fields;
        for_current_user = kwargs.for_current_user ?? false;
        add_followers = kwargs.add_followers ?? false;

        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailLinkPreview} */
        const MailLinkPreview = this.env["mail.link.preview"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
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

        if (!fields) {
            fields = [
                "body",
                "create_date",
                "date",
                "is_discussion",
                "is_note",
                "message_type",
                "model",
                "pinned_at",
                "res_id",
                "subject",
                "subtype_description",
                "write_date",
            ];
        }

        const notifications = MailNotification._filtered_for_web_client(
            MailNotification._filter([["mail_message_id", "in", ids]]).map((n) => n.id)
        );
        for (const message of MailMessage.browse(ids)) {
            const [data] = this._read_format(message.id, fields, false);
            const thread = message.model && this.env[message.model].browse(message.res_id)[0];
            if (thread) {
                const thread_data = { module_icon: "/base/static/description/icon.png" };
                if (message.model !== "discuss.channel") {
                    thread_data.name = thread.name ?? thread.display_name;
                }
                if (for_current_user && add_followers) {
                    thread_data.selfFollower = mailDataHelpers.Store.one(
                        MailFollowers.browse(
                            MailFollowers.search([
                                ["res_model", "=", message.model],
                                ["res_id", "=", message.res_id],
                                ["partner_id", "=", this.env.user.partner_id],
                            ])
                        ),
                        makeKwArgs({ fields: { is_active: true, partner: [] } })
                    );
                }
                store.add(
                    this.env[message.model].browse(message.res_id),
                    thread_data,
                    makeKwArgs({ as_thread: true })
                );
            }
            Object.assign(data, {
                attachment_ids: mailDataHelpers.Store.many(
                    IrAttachment.browse(message.attachment_ids).sort((a1, a2) => a1.id - a2.id)
                ),
                default_subject:
                    message.model &&
                    message.res_id &&
                    (message.model === "res.fake"
                        ? ResFake._message_compute_subject([message.res_id])
                        : MailThread._message_compute_subject([message.res_id])
                    ).get(message.res_id),
                linkPreviews: mailDataHelpers.Store.many(
                    MailLinkPreview.browse(message.link_preview_ids)
                ),
                notifications: mailDataHelpers.Store.many(
                    notifications.filter(
                        (notification) => notification.mail_message_id == message.id
                    )
                ),
                parentMessage: mailDataHelpers.Store.one(
                    MailMessage.browse(message.parent_id),
                    makeKwArgs({ format_reply: false })
                ),
                reactions: mailDataHelpers.Store.many(
                    MailMessageReaction.browse(message.reaction_ids)
                ),
                recipients: mailDataHelpers.Store.many(
                    ResPartner.browse(message.partner_ids),
                    makeKwArgs({ fields: ["name"] })
                ),
                record_name: thread?.name ?? thread?.display_name,
                scheduledDatetime: false,
                thread: mailDataHelpers.Store.one(
                    message.model && this.env[message.model].browse(message.res_id),
                    makeKwArgs({ as_thread: true, only_id: true })
                ),
            });
            if (message.subtype_id) {
                const [subtype] = MailMessageSubtype.browse(message.subtype_id);
                data.subtype_description = subtype.description;
            }
            if (for_current_user) {
                data["needaction"] = Boolean(
                    this.env.user &&
                        MailNotification.search([
                            ["mail_message_id", "=", message.id],
                            ["is_read", "=", false],
                            ["res_partner_id", "=", this.env.user.partner_id],
                        ]).length
                );
                data["starred"] = message.starred_partner_ids?.includes(this.env.user?.partner_id);
                const trackingValues = MailTrackingValue.browse(message.tracking_value_ids);
                const formattedTrackingValues =
                    MailTrackingValue._tracking_value_format(trackingValues);
                data["trackingValues"] = formattedTrackingValues;
            }
            store.add(this.browse(message.id), data);
        }
        this._author_to_store(ids, store);
    }

    _author_to_store(ids, store) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        for (const message of MailMessage.browse(ids)) {
            const data = { author: false, email_from: message.email_from };
            if (message.author_guest_id) {
                data.author = mailDataHelpers.Store.one(
                    MailGuest.browse(message.author_guest_id),
                    makeKwArgs({ fields: ["avatar_128", "name"] })
                );
            } else if (message.author_id) {
                data.author = mailDataHelpers.Store.one(
                    ResPartner.browse(message.author_id),
                    makeKwArgs({ fields: ["avatar_128", "is_company", "name", "user"] })
                );
            }
            store.add(this.browse(message.id), data);
        }
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
        const messages = this.browse(ids);
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

    unlink() {
        const messageByPartnerId = {};
        for (const message of this) {
            for (const partnerId of message.partner_ids) {
                messageByPartnerId[partnerId] ??= [];
                messageByPartnerId[partnerId].push(message);
            }
            if (
                this.env["mail.notification"]
                    .browse(message.notification_ids)
                    .some(({ failure_type }) => Boolean(failure_type))
            ) {
                messageByPartnerId[message.author_id] ??= [];
                messageByPartnerId[message.author_id].push(message);
            }
        }
        for (const [partnerId, messages] of Object.entries(messageByPartnerId)) {
            const [partner] = this.env["res.partner"].browse(parseInt(partnerId));
            this.env["bus.bus"]._sendone(partner, "mail.message/delete", {
                message_ids: messages.map(({ id }) => id),
            });
        }
        return super.unlink(...arguments);
    }

    /** @param {number[]} ids */
    toggle_message_starred(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const messages = this.browse(ids);
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
     * @param {number} partner_id
     * @param {number} guest_id
     * @param {string} action
     * @param {import("@mail/../tests/mock_server/mail_mock_server").mailDataHelpers.Store} store
     */
    _message_reaction(id, content, partner_id, guest_id, action, store) {
        ({ id, content, partner_id, guest_id, action, store } = getKwArgs(
            arguments,
            "id",
            "content",
            "partner_id",
            "guest_id",
            "action",
            "store"
        ));

        /** @type {import("mock_models").MailMessageReaction} */
        const MailMessageReaction = this.env["mail.message.reaction"];

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
        this._reaction_group_to_store(id, store, content);
        this._bus_send_reaction_group(id, content);
    }

    _bus_send_reaction_group(id, content) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        const store = new mailDataHelpers.Store();
        this._reaction_group_to_store(id, store, content);
        BusBus._sendone(
            this._bus_notification_target(id),
            "mail.record/insert",
            store.get_result()
        );
    }

    _reaction_group_to_store(id, store, content) {
        /** @type {import("mock_models").MailMessageReaction} */
        const MailMessageReaction = this.env["mail.message.reaction"];

        const reactions = MailMessageReaction.search([
            ["message_id", "=", id],
            ["content", "=", content],
        ]);
        let reaction_group = mailDataHelpers.Store.many(
            MailMessageReaction.browse(reactions),
            "ADD"
        );
        if (reactions.length === 0) {
            reaction_group = [["DELETE", { message: this.browse(id), content: content }]];
        }
        store.add(this.browse(id), { reactions: reaction_group });
    }

    /**
     * @param {DomainListRepr} domain
     * @param {number} [before]
     * @param {number} [after]
     * @param {number} [limit=30]
     * @returns {Object[]}
     */
    _message_fetch(domain, search_term, before, after, around, limit) {
        ({
            domain,
            search_term,
            before,
            after,
            around,
            limit = 30,
        } = getKwArgs(arguments, "domain", "search_term", "before", "after", "around", "limit"));

        const res = {};
        if (search_term) {
            search_term = search_term.replace(" ", "%");
            domain.push(["body", "ilike", search_term]);
            res.count = this.search_count(domain);
        }
        if (around !== undefined) {
            const messagesBefore = this._filter(domain.concat([["id", "<=", around]])).sort(
                (m1, m2) => m2.id - m1.id
            );
            messagesBefore.length = Math.min(messagesBefore.length, limit / 2);
            const messagesAfter = this._filter(domain.concat([["id", ">", around]])).sort(
                (m1, m2) => m1.id - m2.id
            );
            messagesAfter.length = Math.min(messagesAfter.length, limit / 2);
            const messages = messagesAfter
                .concat(messagesBefore.reverse())
                .sort((m1, m2) => m2.id - m1.id);
            return { ...res, messages };
        }
        if (before) {
            domain.push(["id", "<", before]);
        }
        if (after) {
            domain.push(["id", ">", after]);
        }
        const messages = this._filter(domain).sort((m1, m2) => m2.id - m1.id);
        // pick at most 'limit' messages
        messages.length = Math.min(messages.length, limit);
        res.messages = messages;
        return res;
    }

    /**
     * @param {number[]} ids
     * @param {import("@mail/../tests/mock_server/mail_mock_server").mailDataHelpers.Store} store
     */
    _message_notifications_to_store(ids, store) {
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        for (const message of this.browse(ids)) {
            store.add(this.browse(message.id), {
                author: mailDataHelpers.Store.one(
                    this.env["res.partner"].browse(message.author_id),
                    makeKwArgs({ only_id: true })
                ),
                body: message.body,
                date: message.date,
                message_type: message.message_type,
                notifications: mailDataHelpers.Store.many(
                    MailNotification._filtered_for_web_client(
                        MailNotification.search([["mail_message_id", "=", message.id]])
                    )
                ),
                thread: mailDataHelpers.Store.one(
                    message.model ? this.env[message.model].browse(message.res_id) : false,
                    makeKwArgs({
                        as_thread: true,
                        fields: [
                            "modelName",
                            message.model === "discuss.channel" ? "name" : "display_name",
                        ],
                    })
                ),
            });
        }
    }

    _cleanup_side_records([id]) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [message] = this.browse(id);
        const outdatedStarredPartners = ResPartner.browse(message.starred_partner_ids);
        this.write([message.id], { starred_partner_ids: [Command.clear()] });
        if (outdatedStarredPartners.length === 0) {
            return;
        }
        const notifications = [];
        for (const partner of outdatedStarredPartners) {
            notifications.push([
                partner,
                "mail.record/insert",
                new mailDataHelpers.Store("mail.thread", {
                    counter: MailMessage.search([["starred_partner_ids", "in", partner.id]]).length,
                    counter_bus_id: this.env["bus.bus"].lastBusNotificationId,
                    id: "starred",
                    messages: mailDataHelpers.Store.many(
                        MailMessage.browse(message.id),
                        "DELETE",
                        makeKwArgs({ only_id: true })
                    ),
                    model: "mail.box",
                }).get_result(),
            ]);
        }
        BusBus._sendmany(notifications);
    }
}
