import { Store } from "@mail/../tests/mock_server/store";

import { fields, getKwArgs, models, serverState } from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";

/** @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr */

export class MailMessage extends models.ServerModel {
    _name = "mail.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });
    pinned_at = fields.Generic({ default: false });

    /** @type {typeof models.Model["prototype"]["create"]} */
    create(vals) {
        for (const values of Array.isArray(vals) ? vals : [vals]) {
            // mock: a guest-authored message has no partner author (python defaults author_id to
            // False; the mock field default would otherwise set it to the current user).
            if (values.author_guest_id && !values.author_id) {
                values.author_id = false;
            }
        }
        return super.create(vals);
    }

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

    _store_message_fields(
        res,
        { format_reply = true, chatter_fields, inbox_fields = false, followers } = {}
    ) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").ResFake} */
        const ResFake = this.env["res.fake"];

        res.many("attachment_ids", "_store_attachment_fields", {
            sort: "id",
            dynamic_fields: "_store_attachment_dynamic_fields",
            sudo: true,
        });
        res.one("author_guest_id", "_store_avatar_fields", { sudo: true });
        res.one(
            "author_id",
            (r) => {
                r.attr("is_company");
                r.one("main_user_id", ["partner_id", "share"]);
                r.many("user_ids", ["active", "company_ids", "share"], {
                    internal: true,
                    sudo: true,
                });
                r.from_method("_store_avatar_fields");
            },
            { dynamic_fields: "_store_author_dynamic_fields", sudo: true }
        );
        res.attr("body", (m) => ["markup", m.body]); // mock: html fields must be markup-wrapped
        res.extend(["create_date", "date"]);
        res.attr("email_from", undefined, {
            predicate: (m) => res.is_for_internal_users() || (!m.author_id && !m.author_guest_id),
        });
        // keep "model" for iOS app
        res.extend(["incoming_email_cc", "incoming_email_to", "message_type", "model"]);
        res.many("partner_ids", (r) => r.from_method("_store_avatar_fields"), {
            dynamic_fields: "_store_partner_name_dynamic_fields",
            sort: "id",
            sudo: true,
        });
        res.many("partner_cc_ids", (r) => r.from_method("_store_avatar_fields"), {
            dynamic_fields: "_store_partner_name_dynamic_fields",
            predicate: (m) => m.model !== "discuss.channel",
            sort: "id",
            sudo: true,
        });
        res.attr("pinned_at");
        res.from_method("_store_reaction_group_fields");
        res.attr("reply_to", undefined, {
            predicate: (m) => res.is_for_internal_users() || (!m.author_id && !m.author_guest_id),
        });
        // keep "record_name" and "res_id" for iOS app
        res.extend(["record_name", "res_id"]);
        res.attr("subject");
        res.one("subtype_id", ["description"], { sudo: true });
        res.attr("write_date");
        this._store_linked_messages_fields(res);
        this._store_message_link_previews_fields(res);
        if (res.is_for_internal_users()) {
            res.many("notification_ids", "_store_notification_fields", { sudo: true });
        }

        const followerByRecordAndPartner = {};
        const followerKey = (model, resId) => `${model}\x00${resId}`;
        if (res.is_for_current_user() && inbox_fields && this.env.user) {
            for (const message of this) {
                if (!message.model || message.model === "discuss.channel" || !message.res_id) {
                    continue;
                }
                const [follower] = MailFollowers.browse(
                    MailFollowers.search([
                        ["res_model", "=", message.model],
                        ["res_id", "=", message.res_id],
                        ["partner_id", "=", this.env.user.partner_id],
                    ])
                );
                if (follower) {
                    followerByRecordAndPartner[followerKey(message.model, message.res_id)] =
                        follower.id;
                }
            }
        }
        res.one(
            "thread",
            (r) => {
                const threadModel = r.records?._name;
                // sudo: mail.thread - if mentionned in a non accessible thread, name is allowed
                r.attr("display_name", (t) => t.name ?? t.display_name, { sudo: true });
                r.attr("has_mail_thread", () =>
                    Boolean(this.env[threadModel]?._inherit?.includes("mail.thread"))
                );
                r.attr("module_icon", () => "/base/static/description/icon.png", {
                    predicate: () => inbox_fields,
                });
                r.one("selfFollower", ["is_active", "partner_id"], {
                    predicate: () =>
                        res.is_for_current_user() &&
                        inbox_fields &&
                        threadModel !== "discuss.channel",
                    value: (t) =>
                        MailFollowers.browse(
                            followerByRecordAndPartner[followerKey(threadModel, t.id)]
                        ),
                });
                r.attr("priority", (t) => t.priority, {
                    predicate: (t) => inbox_fields && t.priority,
                    sudo: true,
                });
                r.attr(
                    "priority_definition",
                    () => this.env[threadModel].fields_get(["priority"])["priority"]["selection"],
                    { predicate: (t) => inbox_fields && t.priority }
                );
            },
            { as_thread: true }
        );
        if (res.is_for_current_user()) {
            res.attr("is_bookmarked", (m) =>
                Boolean(m.bookmarked_partner_ids?.includes(this.env.user?.partner_id))
            );
        }
        res.attr("default_subject", (m) => {
            if (!m.model || !m.res_id) {
                return false;
            }
            return (
                m.model === "res.fake"
                    ? ResFake._message_compute_subject([m.res_id])
                    : MailThread._message_compute_subject([m.res_id])
            ).get(m.res_id);
        });
        res.attr("scheduledDatetime", () => false);
        if (res.is_for_current_user()) {
            res.attr("needaction", (m) => this._needaction(m));
        }
        // Add extras at the end to guarantee order in result.
        this._store_extra_fields(res, { format_reply });

        // discuss override: call history and parent message (format_reply)
        res.many("call_history_ids", ["duration_hour", "end_dt"], {
            predicate: (m) => m.body && m.body.includes('data-oe-type="call"'),
        });
    }

    _needaction(message) {
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        return Boolean(
            this.env.user &&
                MailNotification.search([
                    ["mail_message_id", "=", message.id],
                    ["is_read", "=", false],
                    ["res_partner_id", "=", this.env.user.partner_id],
                ]).length
        );
    }

    _store_message_link_previews_fields(res) {
        /** @type {import("mock_models").MailMessageLinkPreview} */
        const MailMessageLinkPreview = this.env["mail.message.link.preview"];
        res.many("message_link_preview_ids", "_store_message_link_preview_fields", {
            value: (m) =>
                MailMessageLinkPreview.browse(m.message_link_preview_ids).filter(
                    (lpm) => !lpm.is_hidden
                ),
            sort: (lpm1, lpm2) => lpm1.sequence - lpm2.sequence || lpm1.id - lpm2.id,
        });
    }

    _store_author_dynamic_fields(res) {
        this._store_partner_name_dynamic_fields(res);
    }

    _store_attachment_dynamic_fields(attachmentRes) {
        if (attachmentRes.is_for_current_user() && this.is_current_user_or_guest_author) {
            attachmentRes.from_method("_store_ownership_fields");
        }
    }

    _store_partner_name_dynamic_fields(res) {
        res.attr("name");
    }

    _store_extra_fields(res, { format_reply } = {}) {
        if (format_reply) {
            // discuss override: parent message of channel messages
            res.one("parent_id", "_store_message_fields", {
                fields_params: { format_reply: false },
                predicate: (m) => m.model === "discuss.channel",
                sudo: true,
            });
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

    mark_as_unread(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        const messages = this.browse(ids);
        const notifications = MailNotification._filter([
            ["mail_message_id", "in", messages.map((messages) => messages.id)],
            ["res_partner_id", "=", this.env.user.partner_id],
            ["notification_type", "=", "inbox"],
        ]);
        if (notifications.length === 0) {
            return;
        }
        MailNotification.write(
            notifications.map((e) => e.id),
            { is_read: false, read_date: false }
        );
        for (const message of messages) {
            BusBus._sendone(
                this._bus_notification_target(message.id),
                "mail.message/mark_as_unread",
                {
                    message_ids: [message.id],
                    store_data: new Store()
                        .add(this.browse(message.id), "_store_message_fields")
                        .as_dict(),
                }
            );
        }
    }

    unlink() {
        const messageByPartnerId = {};
        for (const message of this) {
            for (const partnerId of [...message.partner_ids, ...message.partner_cc_ids]) {
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
     * @param {import("@mail/../tests/mock_server/store").Store} store
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
        if (store) {
            store.add(this.browse(id), "_store_reaction_group_fields", {
                fields_params: { content },
            });
        }
        this._bus_send_reaction_group(id, content);
    }

    _bus_send_reaction_group(id, content) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        const store = new Store();
        store.add(this.browse(id), "_store_reaction_group_fields", { fields_params: { content } });
        BusBus._sendone(this._bus_notification_target(id), "mail.record/insert", store.as_dict());
    }

    _store_reaction_group_fields(res, { content = null } = {}) {
        /** @type {import("mock_models").MailMessageReaction} */
        const MailMessageReaction = this.env["mail.message.reaction"];

        const messageIds = res.records.map((m) => m.id);
        const filter_content = content != null;
        let reactions;
        if (filter_content) {
            reactions = MailMessageReaction.browse(
                MailMessageReaction.search([
                    ["message_id", "in", messageIds],
                    ["content", "=", content],
                ])
            );
        } else {
            reactions = MailMessageReaction.browse(
                MailMessageReaction.search([["message_id", "in", messageIds]])
            );
        }
        const reactionsByMessage = {};
        for (const reaction of reactions) {
            (reactionsByMessage[reaction.message_id] ??= []).push(reaction);
        }
        res.many("reactions", [], {
            mode: filter_content ? "ADD" : "REPLACE",
            predicate: (m) => !filter_content || m.id in reactionsByMessage,
            value: (m) => {
                const byContent = {};
                for (const reaction of reactionsByMessage[m.id] ?? []) {
                    (byContent[reaction.content] ??= []).push(reaction);
                }
                return Object.entries(byContent).map(([groupContent, groupReactions]) => ({
                    content: groupContent,
                    count: groupReactions.length,
                    guests: groupReactions.filter((r) => r.guest_id).map((r) => r.guest_id),
                    message: m.id,
                    partners: groupReactions.filter((r) => r.partner_id).map((r) => r.partner_id),
                    sequence: Math.min(...groupReactions.map((r) => r.id)),
                }));
            },
        });
        if (filter_content) {
            res.many("reactions", [], {
                mode: "DELETE",
                predicate: (m) => !(m.id in reactionsByMessage),
                value: (m) => ({ message: m.id, content }),
            });
        }
        res.many(
            "reaction_ids",
            (r) => {
                r.one("partner_id", "_store_avatar_fields", {
                    dynamic_fields: (avatarRes, reaction) =>
                        this.browse(reaction.message_id)._store_partner_name_dynamic_fields(
                            avatarRes
                        ),
                    only_data: true,
                });
                r.one("guest_id", "_store_avatar_fields", { only_data: true });
            },
            {
                only_data: true,
                predicate: (m) => m.id in reactionsByMessage,
                value: (m) =>
                    MailMessageReaction.browse((reactionsByMessage[m.id] ?? []).map((r) => r.id)),
            }
        );
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
            const authorIds = this.env["res.partner"].search([["name", "ilike", search_term]]);
            const guestIds = this.env["mail.guest"].search([["name", "ilike", search_term]]);
            let message_domain = Domain.or([
                [["body", "ilike", search_term]],
                [["attachment_ids", "in", irAttachmentIds]],
                [["author_id", "in", authorIds]],
                [["author_guest_id", "in", guestIds]],
                [["subject", "ilike", search_term]],
                [["subtype_ids", "in", subtypeIds]],
            ]);
            if (thread && is_notification !== false) {
                const messageIds = this.search([
                    ["res_id", "=", parseInt(thread[0].id)],
                    ["model", "=", thread._name],
                ]);
                message_domain = Domain.or([
                    message_domain,
                    new Domain([["id", "in", messageIds]]),
                ]);
            }
            domain = Domain.and([domain, message_domain]).toList();
        }
        if (search_term || is_notification !== undefined) {
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

    _linked_message_ids(message) {
        const body = message?.body || "";
        const doc = new DOMParser().parseFromString(body, "text/html");
        const anchors = doc.querySelectorAll(
            'a.o_message_redirect[data-oe-model="mail.message"][data-oe-id]'
        );
        const mids = [];
        for (const a of anchors) {
            const id = parseInt(a.getAttribute("data-oe-id"), 10);
            if (!Number.isNaN(id)) {
                mids.push(id);
            }
        }
        // search all messages, not only `this` (linked messages are usually not in the recordset)
        return this.env["mail.message"]
            ._filter([
                ["id", "in", mids],
                ["model", "!=", false],
                ["res_id", "!=", false],
            ])
            .map((m) => m.id);
    }

    _store_linked_messages_fields(res) {
        res.many(
            "linked_message_ids",
            (r) => {
                r.extend(["model", "res_id"]);
                // sudo: mail.thread - reading record name of accessible message is acceptable
                r.one("thread", ["display_name"], { as_thread: true, sudo: true });
            },
            {
                only_data: true,
                // browse on the model (not `this`): linked messages are usually not in the recordset
                value: (m) => this.env["mail.message"].browse(this._linked_message_ids(m)),
            }
        );
    }

    _store_notification_fields(res) {
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        res.extend(["author_id", "author_guest_id", "date", "message_type"]);
        res.attr("body", (m) => ["markup", m.body]); // mock: html fields must be markup-wrapped
        res.many("notification_ids", "_store_notification_fields", {
            value: (m) =>
                MailNotification.browse(
                    MailNotification._filtered_for_web_client(
                        MailNotification.search([["mail_message_id", "=", m.id]])
                    ).map((n) => n.id)
                ),
        });
        res.one(
            "thread",
            (r) => {
                const threadModel = r.records?._name;
                r.attr("modelName", () => this.env[threadModel]._description ?? threadModel);
                r.attr("display_name");
            },
            { as_thread: true }
        );
    }

    /**
     * @param {number[]} ids
     * @param {import("@mail/../tests/mock_server/store").Store} store
     */
    _message_notifications_to_store(ids, store) {
        store.add(this.browse(ids), "_store_notification_fields");
    }
}
