import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import {
    Command,
    fields,
    getKwArgs,
    makeKwArgs,
    models,
    serverState,
} from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";

/** @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr */

export class MailMessage extends models.ServerModel {
    _name = "mail.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });
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
    _to_store(store, fields, for_current_user, add_followers) {
        const kwargs = getKwArgs(arguments, "store", "fields", "for_current_user", "add_followers");
        store = kwargs.store;
        fields = kwargs.fields;
        for_current_user = kwargs.for_current_user ?? false;
        add_followers = kwargs.add_followers ?? false;

        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailMessageLinkPreview} */
        const MailMessageLinkPreview = this.env["mail.message.link.preview"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").MailTrackingValue} */
        const MailTrackingValue = this.env["mail.tracking.value"];
        /** @type {import("mock_models").ResFake} */
        const ResFake = this.env["res.fake"];

        const notifications = MailNotification._filtered_for_web_client(
            MailNotification._filter([["mail_message_id", "in", this.map((m) => m.id)]]).map(
                (n) => n.id
            )
        );
        store._add_record_fields(
            this,
            fields.filter((field) => !["notification_ids", "mail_link_preview_ids"].includes(field))
        );
        for (const message of this) {
            const thread = message.model && this.env[message.model].browse(message.res_id)[0];
            if (thread) {
                const thread_data = {
                    display_name: thread.name ?? thread.display_name,
                    module_icon: "/base/static/description/icon.png",
                };
                if (for_current_user && add_followers) {
                    thread_data.selfFollower = mailDataHelpers.Store.one(
                        MailFollowers.browse(
                            MailFollowers.search([
                                ["res_model", "=", message.model],
                                ["res_id", "=", message.res_id],
                                ["partner_id", "=", this.env.user.partner_id],
                            ])
                        ),
                        makeKwArgs({
                            fields: ["is_active", mailDataHelpers.Store.one("partner_id", [])],
                        })
                    );
                }
                store._add_record_fields(
                    this.env[message.model].browse(message.res_id),
                    thread_data,
                    makeKwArgs({ as_thread: true })
                );
            }
            const data = {
                default_subject:
                    message.model &&
                    message.res_id &&
                    (message.model === "res.fake"
                        ? ResFake._message_compute_subject([message.res_id])
                        : MailThread._message_compute_subject([message.res_id])
                    ).get(message.res_id),
                record_name: thread?.name ?? thread?.display_name,
                scheduledDatetime: false,
                thread: mailDataHelpers.Store.one(
                    message.model && this.env[message.model].browse(message.res_id),
                    makeKwArgs({ as_thread: true, only_id: true })
                ),
            };
            if (fields.includes("message_link_preview_ids")) {
                data.message_link_preview_ids = mailDataHelpers.Store.many(
                    MailMessageLinkPreview.browse(message.message_link_preview_ids).filter(
                        (lpm) => !lpm.is_hidden
                    )
                );
            }
            if (fields.includes("notification_ids")) {
                data.notification_ids = mailDataHelpers.Store.many(
                    notifications.filter(
                        (notification) => notification.mail_message_id == message.id
                    )
                );
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
            store._add_record_fields(this.browse(message.id), data);
        }
        this._author_to_store(store);
        this._store_add_linked_messages(store);
    }

    get _to_store_defaults() {
        return [
            mailDataHelpers.Store.many(
                "attachment_ids",
                makeKwArgs({
                    sort: (a1, a2) => a1.id - a2.id,
                })
            ),
            mailDataHelpers.Store.attr("body", (m) => ["markup", m.body]),
            "create_date",
            "date",
            "message_type",
            "model",
            "message_link_preview_ids",
            "notification_ids",
            mailDataHelpers.Store.one("parent_id", makeKwArgs({ format_reply: false })),
            mailDataHelpers.Store.many("partner_ids", makeKwArgs({ fields: ["name"] })),
            "pinned_at",
            mailDataHelpers.Store.attr("reactions", (m) =>
                mailDataHelpers.Store.many(this.env["mail.message.reaction"].browse(m.reaction_ids))
            ),
            "res_id",
            "subject",
            "write_date",
            mailDataHelpers.Store.one(
                "subtype_id",
                makeKwArgs({
                    fields: ["description"],
                    predicate: (m) => m.subtype_id,
                })
            ),
        ];
    }

    _author_to_store(store) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        for (const message of this) {
            const data = {
                author_id: false,
                author_guest_id: false,
                email_from: message.email_from,
            };
            if (message.author_guest_id) {
                data.author_guest_id = mailDataHelpers.Store.one(
                    MailGuest.browse(message.author_guest_id),
                    makeKwArgs({ fields: ["avatar_128", "name"] })
                );
            } else if (message.author_id) {
                data.author_id = mailDataHelpers.Store.one(
                    ResPartner.browse(message.author_id),
                    makeKwArgs({ fields: ["avatar_128", "is_company", "name", "user"] })
                );
            }
            store._add_record_fields(MailMessage.browse(message.id), data);
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
        const store = new mailDataHelpers.Store();
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
            store.add(this.browse(message.id), { starred: !wasStarred });
        }
        return store.get_result();
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
            makeKwArgs({ mode: "ADD" })
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
    _message_fetch(domain, thread, search_term, is_notification, before, after, around, limit) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];
        /** @type {import("mock_models").MailTrackingValue} */
        const MailTrackingValue = this.env["mail.tracking.value"];
        ({
            domain,
            thread,
            search_term,
            is_notification,
            before,
            after,
            around,
            limit = 30,
        } = getKwArgs(
            arguments,
            "domain",
            "thread",
            "search_term",
            "is_notification",
            "before",
            "after",
            "around",
            "limit"
        ));
        const res = {};
        if (thread) {
            domain = domain.concat([
                ["res_id", "=", parseInt(thread[0].id)],
                ["model", "=", thread._name],
                ["message_type", "!=", "user_notification"],
            ]);
        }
        if (is_notification === true) {
            domain.push(["message_type", "=", "notification"]);
        } else if (is_notification === false) {
            domain.push(["message_type", "!=", "notification"]);
        }
        if (search_term) {
            domain = new Domain(domain || []);
            search_term = search_term.replace(" ", "%");
            const subtypeIds = MailMessageSubtype.search([["description", "ilike", search_term]]);
            const irAttachmentIds = IrAttachment.search([["name", "ilike", search_term]]);
            let message_domain = Domain.or([
                [["body", "ilike", search_term]],
                [["attachment_ids", "in", irAttachmentIds]],
                [["subject", "ilike", search_term]],
                [["subtype_ids", "in", subtypeIds]],
            ]);
            if (thread && is_notification !== false) {
                const messageIds = this.search([
                    ["res_id", "=", parseInt(thread[0].id)],
                    ["model", "=", thread._name],
                ]);
                const trackingValueDomain = Domain.and([
                    [["mail_message_id", "in", messageIds]],
                    this._get_tracking_values_domain(search_term),
                ]).toList();
                const trackingValueIds = MailTrackingValue.search(trackingValueDomain);
                const trackingMessageIds = this.search([
                    ["tracking_value_ids", "in", trackingValueIds],
                ]);
                message_domain = Domain.or([
                    message_domain,
                    new Domain([["id", "in", trackingMessageIds]]),
                ]);
            }
            domain = Domain.and([domain, message_domain]).toList();
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

    _get_tracking_values_domain(search_term) {
        let numeric_term = false;
        const epsilon = 1e-9;
        numeric_term = parseFloat(search_term);
        const field_names = [
            "old_value_char",
            "new_value_char",
            "old_value_text",
            "new_value_text",
            "old_value_datetime",
            "new_value_datetime",
        ];
        let domain = Domain.or(
            field_names.map((field_name) => new Domain([[field_name, "ilike", search_term]]))
        );
        if (numeric_term) {
            const float_domain = Domain.or(
                ["old_value_float", "new_value_float"].map(
                    (fieldName) =>
                        new Domain([
                            [fieldName, ">=", numeric_term - epsilon],
                            [fieldName, "<=", numeric_term + epsilon],
                        ])
                )
            );
            domain = Domain.or([domain, float_domain]);
        }
        if (Number.isInteger(numeric_term)) {
            domain = Domain.or([
                domain,
                new Domain([["old_value_integer", "=", numeric_term]]),
                new Domain([["new_value_integer", "=", numeric_term]]),
            ]);
        }
        return domain;
    }

    /**
     * @param {import("@mail/../tests/mock_server/mail_mock_server").mailDataHelpers.Store} store
     */
    _store_add_linked_messages(store) {
        const mids = [];
        for (const message of this) {
            const body = message?.body || "";
            const doc = new DOMParser().parseFromString(body, "text/html");
            const anchors = doc.querySelectorAll(
                'a.o_message_redirect[data-oe-model="mail.message"][data-oe-id]'
            );
            for (const a of anchors) {
                const idStr = a.getAttribute("data-oe-id");
                const id = parseInt(idStr, 10);
                if (!Number.isNaN(id)) {
                    mids.push(id);
                }
            }
        }
        for (const message of this.env["mail.message"]._filter([["id", "in", mids]])) {
            if (message.model && message.res_id) {
                const record = this.env[message.model]._filter([["id", "=", message.res_id]]);
                store.add(
                    this.env["mail.message"].browse(message.id),
                    makeKwArgs({
                        fields: [
                            "model",
                            "res_id",
                            mailDataHelpers.Store.attr(
                                "thread",
                                mailDataHelpers.Store.one(
                                    this.env[message.model].browse(record.id),
                                    makeKwArgs({ fields: ["display_name"] })
                                )
                            ),
                        ],
                    })
                );
            }
        }
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
                author_id: mailDataHelpers.Store.one(
                    this.env["res.partner"].browse(message.author_id),
                    makeKwArgs({ only_id: true })
                ),
                body: message.body,
                date: message.date,
                message_type: message.message_type,
                notification_ids: mailDataHelpers.Store.many(
                    MailNotification._filtered_for_web_client(
                        MailNotification.search([["mail_message_id", "=", message.id]])
                    )
                ),
                thread: mailDataHelpers.Store.one(
                    message.model ? this.env[message.model].browse(message.res_id) : false,
                    makeKwArgs({ as_thread: true, fields: ["modelName", "display_name"] })
                ),
            });
        }
    }
}
