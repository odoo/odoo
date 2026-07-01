import { Store } from "@mail/../tests/mock_server/store";
import { parseEmail } from "@mail/utils/common/format";

import { serializeDateTime } from "@web/core/l10n/dates";
import {
    Command,
    getKwArgs,
    makeKwArgs,
    models,
    unmakeKwArgs,
} from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

export class MailThread extends models.ServerModel {
    _name = "mail.thread";
    _inherit = ["base"];

    /**
     * @param {number[]} ids
     * @param {number} [after]
     * @param {number} [limit=100]
     * @param {boolean} [filter_recipients]
     */
    message_get_followers(ids, after, limit, filter_recipients) {
        const kwargs = getKwArgs(arguments, "ids", "after", "limit", "filter_recipients");
        ids = kwargs.ids;
        after = kwargs.after || 0;
        limit = kwargs.limit || 100;
        filter_recipients = kwargs.filter_recipients || false;

        return new Store()
            .add(this.browse(ids), "_store_message_followers_fields", {
                as_thread: true,
                fields_params: { after, limit, filter_recipients },
            })
            .as_dict();
    }

    _store_message_followers_fields(
        res,
        { after = 0, limit = 100, filter_recipients = false, reset = false } = {}
    ) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        const followersByThread = (thread) => {
            const domain = [
                ["res_id", "=", thread.id],
                ["res_model", "=", this._name],
                ["partner_id", "!=", this.env.user.partner_id],
            ];
            if (filter_recipients) {
                // subtype and partner active checks not done here for simplicity
            }
            if (after) {
                domain.push(["id", ">", after]);
            }
            const followers = MailFollowers._filter(domain).sort(
                (f1, f2) => f1.id - f2.id // sorted from lowest ID to highest ID (i.e. from oldest to youngest)
            );
            followers.length = Math.min(followers.length, limit);
            return MailFollowers.browse(followers.map((follower) => follower.id));
        };
        res.many(filter_recipients ? "recipients" : "followers", "_store_follower_fields", {
            value: followersByThread,
            mode: reset ? "REPLACE" : "ADD",
        });
    }

    /** @param {number[]} ids */
    message_post(ids) {
        const kwargs = getKwArgs(arguments, "ids", "subtype_id");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];

        const id = ids[0]; // ensure_one
        if (kwargs.context?.mail_post_autofollow && kwargs.partner_ids?.length) {
            MailThread.message_subscribe.call(this, ids, kwargs.partner_ids, []);
        }
        if (kwargs.attachment_ids) {
            const attachments = IrAttachment._filter([
                ["id", "in", kwargs.attachment_ids],
                ["res_model", "=", "mail.compose.message"],
                ["res_id", "=", false],
            ]);
            const attachmentIds = attachments.map((attachment) => attachment.id);
            IrAttachment.write(attachmentIds, {
                res_id: id,
                res_model: this._name,
            });
            kwargs.attachment_ids = attachmentIds.map((attachmentId) => Command.link(attachmentId));
        }
        let author_id;
        let email_from;
        const author_guest_id =
            ResUsers._is_public(this.env.uid) && MailGuest._get_guest_from_context()?.id;
        if (!author_guest_id) {
            [author_id, email_from] = MailThread._message_compute_author.call(
                this,
                kwargs.author_id,
                kwargs.email_from
            );
        }
        email_from ||= false;
        const message_type = kwargs.message_type || "notification";
        const values = unmakeKwArgs({
            ...kwargs,
            author_id,
            author_guest_id,
            email_from,
            message_type,
            subtype_id: MailMessageSubtype._filter([
                ["subtype_xmlid", "=", kwargs.subtype_xmlid || "mail.mt_note"],
            ])[0]?.id,
            model: this._name,
            res_id: id,
        });
        delete values.context;
        delete values.subtype_xmlid;
        const messageId = MailMessage.create(values);
        for (const partnerId of kwargs.partner_ids || []) {
            MailNotification.create({
                mail_message_id: messageId,
                notification_type: "inbox",
                res_partner_id: partnerId,
            });
        }
        MailThread._notify_thread.call(this, ids, messageId, kwargs.context?.temporary_id);
        return [messageId];
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partner_ids
     * @param {number[]} subtype_ids
     */
    message_subscribe(ids, partner_ids, subtype_ids) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids", "subtype_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];
        subtype_ids = kwargs.subtype_ids || [];

        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];

        for (const id of ids) {
            for (const partner_id of partner_ids) {
                let followerId = MailFollowers.search([["partner_id", "=", partner_id]])[0];
                if (!followerId) {
                    if (!subtype_ids?.length) {
                        subtype_ids = MailMessageSubtype.search([
                            ["default", "=", true],
                            "|",
                            ["res_model", "=", this._name],
                            ["res_model", "=", false],
                        ]);
                    }
                    followerId = MailFollowers.create({
                        is_active: true,
                        partner_id,
                        res_id: id,
                        res_model: this._name,
                        subtype_ids: subtype_ids,
                    });
                }
                this.env[this._name].write(ids, {
                    message_follower_ids: [Command.link(followerId)],
                });
            }
        }
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partner_ids
     */
    message_unsubscribe(ids, partner_ids) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];

        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        if (!partner_ids.length) {
            return true;
        }
        const followers = MailFollowers.search([
            ["res_model", "=", this._name],
            ["res_id", "in", ids],
            ["partner_id", "in", partner_ids],
        ]);
        MailFollowers.unlink(followers);
    }

    /**
     * Note that this method is overridden by snailmail module but not simulated here.
     *
     * @param {string} notification_type
     */
    notify_cancel_by_type(notification_type) {
        const kwargs = getKwArgs(arguments, "notification_type");
        notification_type = kwargs.notification_type;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        // Query matching notifications
        const notifications = MailNotification._filter([
            ["notification_type", "=", notification_type],
            ["notification_status", "in", ["bounce", "exception"]],
        ]).filter((notification) => {
            const [message] = MailMessage.browse(notification.mail_message_id);
            return message.model === this._name && message.author_id === this.env.user.partner_id;
        });
        // Update notification status
        MailNotification.write(
            notifications.map((notification) => notification.id),
            { notification_status: "canceled" }
        );
        // Send bus notifications to update status of notifications in the web client
        const [partner] = ResPartner.read(this.env.user.partner_id);
        const store = new Store();
        MailMessage._message_notifications_to_store(
            notifications.map((notification) => notification.mail_message_id),
            store
        );
        BusBus._sendone(partner, "mail.record/insert", store.as_dict());
    }

    /**
     * @param {number} id
     * @param {Object} result
     * @param {number} partner
     * @param {string} email
     * @param {string} lang
     * @param {string} reason
     * @param {string} name
     */
    _message_add_suggested_recipient(id, result, partner, email, lang, reason = "", name) {
        const kwargs = getKwArgs(
            arguments,
            "id",
            "result",
            "partner",
            "email",
            "lang",
            "reason",
            "name"
        );
        id = kwargs.id;
        delete kwargs.id;
        result = kwargs.result;
        partner = kwargs.partner;
        email = kwargs.email;
        lang = kwargs.lang;
        reason = kwargs.reason;
        name = kwargs.name;

        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (email !== undefined && partner === undefined) {
            const partnerInfo = parseEmail(email);
            partner = ResPartner._filter([["email", "=", partnerInfo[1]]])[0];
        }
        if (partner) {
            result.push({
                partner_id: partner.id,
                name: partner.display_name,
                email: partner.email,
                lang,
                reason,
                create_values: {},
                recipient_type: "to",
            });
        } else {
            const partnerCreateValues = this._get_customer_information(id);
            result.push({
                email,
                name,
                lang,
                reason,
                create_values: partnerCreateValues,
                recipient_type: "to",
            });
        }
        return result;
    }

    _get_customer_information(id) {
        return {};
    }

    /**
     * @param {number} id
     * @param {number} message_id
     * @param {boolean} pinned
     * @param {string} model
     */
    set_message_pin(id, message_id, pinned) {
        const kwargs = getKwArgs(arguments, "id", "message_id", "pinned");
        id = kwargs.id;
        delete kwargs.id;
        message_id = kwargs.message_id;
        pinned = kwargs.pinned;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const pinned_at = pinned && serializeDateTime(DateTime.now());
        MailMessage.write([message_id], { pinned_at });
        const [thread] = this.read(id);
        BusBus._sendone(
            thread,
            "mail.record/insert",
            new Store().add(MailMessage.browse(message_id), { pinned_at }).as_dict()
        );
    }

    /**
     * @param {number} [author_id]
     * @param {string} [email_from]
     */
    _message_compute_author(author_id, email_from) {
        const kwargs = getKwArgs(arguments, "author_id", "email_from");
        author_id = kwargs.author_id;
        email_from = kwargs.email_from;

        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (!author_id) {
            // For simplicity partner is not guessed from email_from here, but
            // that would be the first step on the server.
            const [author] = ResPartner.browse(this.env.user.partner_id);
            author_id = author.id;
            email_from = `${author.display_name} <${author.email}>`;
        }
        if (!email_from && author_id) {
            const [author] = ResPartner.browse(author_id);
            email_from = `${author.display_name} <${author.email}>`;
        }
        if (email_from === undefined) {
            if (author_id) {
                const [author] = ResPartner.browse(author_id);
                email_from = `${author.display_name} <${author.email}>`;
            }
        }
        if (!email_from) {
            throw Error("Unable to log message due to missing author email.");
        }
        return [author_id, email_from];
    }

    /** @param {number[]} ids */
    _message_compute_subject(ids) {
        const records = this.browse(ids);
        return new Map(records.map((record) => [record.id, record.name || ""]));
    }

    /** @param {number[]} ids */
    _message_get_suggested_recipients(ids, additional_partners = [], primary_email = false) {
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").ResFake} */
        const ResFake = this.env["res.fake"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        if (this._name === "res.fake") {
            return ResFake._message_get_suggested_recipients(
                ids,
                additional_partners,
                primary_email
            );
        }
        const result = ids.reduce((result, id) => (result[id] = []), {});
        const model = this.env[this._name];
        for (const record in model.browse(ids)) {
            if (record.user_id) {
                const user = ResUsers.browse(record.user_id);
                if (user.partner_id) {
                    const reason = model._fields["user_id"].string;
                    const partner = ResPartner.browse(user.partner_id);
                    MailThread._message_add_suggested_recipient.call(
                        this,
                        result,
                        makeKwArgs({
                            email: partner.email,
                            partner: user.partner_id,
                            reason,
                            recipient_type: "to",
                        })
                    );
                }
            }
        }
        return result;
    }

    /**
     * Simplified version that sends notification to author and channel.
     *
     * @param {number[]} ids
     * @param {number} message_id
     * @param {number} [temporary_id]
     */
    _notify_thread(ids, message_id, temporary_id) {
        const kwargs = getKwArgs(arguments, "ids", "message_id", "temporary_id");
        ids = kwargs.ids;
        delete kwargs.ids;
        message_id = kwargs.message_id;
        temporary_id = kwargs.temporary_id;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const [message] = MailMessage.browse(message_id);
        const notifications = [];
        if (this._name === "discuss.channel") {
            // members
            const channels = DiscussChannel.browse(message.res_id);
            for (const channel of channels) {
                notifications.push([
                    channel,
                    "discuss.channel/new_message",
                    {
                        store_data: new Store()
                            .add(MailMessage.browse(message_id), "_store_message_fields")
                            .as_dict(),
                        id: channel.id,
                        temporary_id,
                    },
                ]);
                const memberOfCurrentUser = this._find_or_create_member_for_self(ids[0]);
                if (memberOfCurrentUser) {
                    this.env["discuss.channel.member"]._set_last_seen_message(
                        [memberOfCurrentUser.id],
                        message.id,
                        false
                    );
                    this.env["discuss.channel.member"]._set_new_message_separator(
                        [memberOfCurrentUser.id],
                        message.id + 1,
                        true
                    );
                }
            }
        }
        if (message.partner_ids) {
            for (const partner_id of message.partner_ids) {
                const [partner] = ResPartner.search_read([["id", "=", partner_id]]);
                if (partner.user_ids.length > 0) {
                    const [user] = ResUsers.search_read([["id", "=", partner.user_ids[0]]]);
                    if (user.notification_type === "inbox") {
                        notifications.push([
                            partner,
                            "mail.message/inbox",
                            {
                                message_id: message.id,
                                store_data: new Store()
                                    .add(MailMessage.browse(message.id), "_store_message_fields", {
                                        fields_params: { inbox_fields: true },
                                    })
                                    .as_dict(),
                            },
                        ]);
                    }
                }
            }
        }
        BusBus._sendmany(notifications);
    }

    /**
     * @param {string[]} fields_iter
     * @param {Object} initial_values_dict
     */
    _message_track(fields_iter, initial_values_dict) {
        const kwargs = getKwArgs(arguments, "fields_iter", "initial_values_dict");
        fields_iter = kwargs.fields_iter;
        initial_values_dict = kwargs.initial_values_dict;

        /** @type {import("mock_models").Base} */
        const Base = this.env["base"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const trackFieldNamesToField = this.env[this._name].fields_get(fields_iter);
        const tracking = {};
        const model = this.env[this._name];
        for (const record of model) {
            tracking[record.id] = Base._mail_track.call(
                this,
                trackFieldNamesToField,
                initial_values_dict[record.id],
                record
            );
        }
        for (const record of model) {
            const { changedFieldNames } = tracking[record.id] || {};
            if (!changedFieldNames || !changedFieldNames.length) {
                continue;
            }
            const changedFieldsInitialValues = {};
            const initialFieldValues = initial_values_dict[record.id];
            for (const fname in changedFieldNames) {
                changedFieldsInitialValues[fname] = initialFieldValues[fname];
            }
            const subtype = MailThread._track_log_get_default_subtype.call(
                this,
                changedFieldsInitialValues
            );
            MailThread.message_post.call(this, [record.id], subtype.id);
        }
        return tracking;
    }

    /** @param {Object} initial_values */
    _track_finalize(initial_values) {
        const kwargs = getKwArgs(arguments, "initial_values");
        initial_values = kwargs.initial_values;

        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        MailThread._message_track.call(
            this,
            MailThread._track_get_fields.call(this),
            initial_values
        );
    }

    _track_get_fields() {
        return Object.entries(this.env[this._name]._fields).reduce((prev, next) => {
            if (next[1].tracking) {
                prev.push(next[0]);
            }
            return prev;
        }, []);
    }

    _track_prepare() {
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const trackedFieldNames = MailThread._track_get_fields.call(this);
        if (!trackedFieldNames.length) {
            return;
        }
        const initialTrackedFieldValuesByRecordId = {};
        for (const record of this.env[this._name]) {
            const values = {};
            initialTrackedFieldValuesByRecordId[record.id] = values;
            for (const fname of trackedFieldNames) {
                values[fname] = record[fname];
            }
        }
        return initialTrackedFieldValuesByRecordId;
    }

    /** @param {Object} track_init_values */
    _track_log_get_default_subtype(track_init_values) {
        return false;
    }

    _store_thread_fields(res, { request_list = [] } = {}) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailActivity} */
        const MailActivity = this.env["mail.activity"];
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailScheduledMessage} */
        const MailScheduledMessage = this.env["mail.scheduled.message"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const model = this.env[this._name];
        if (res.is_for_current_user()) {
            res.attr("hasReadAccess", true); // mock: user has read access by default
            res.attr("hasWriteAccess", (t) => t.hasWriteAccess ?? true); // mock: write access by default
            res.attr("canPostOnReadonly", this._mail_post_access === "read");
        }
        if (request_list.includes("activities") && model.has_activities) {
            res.many("activities", "_store_activity_fields", {
                value: (t) => MailActivity.browse(t.activity_ids),
            });
        }
        if (request_list.includes("attachments")) {
            res.many("attachments", "_store_attachment_fields", {
                value: (t) =>
                    IrAttachment.browse(
                        IrAttachment._filter([
                            ["res_id", "=", t.id],
                            ["res_model", "=", this._name],
                            ["res_field", "=", false],
                        ])
                            .sort((a1, a2) => a1.id - a2.id)
                            .map((attachment) => attachment.id)
                    ),
            });
            res.attr("areAttachmentsLoaded", true);
            res.attr("isLoadingAttachments", false);
            // Specific implementation of mail.thread.main.attachment
            if (model._fields.message_main_attachment_id) {
                res.one("message_main_attachment_id", [], {
                    value: (t) => IrAttachment.browse(t.message_main_attachment_id),
                });
            }
        }
        if (request_list.includes("contact_fields")) {
            res.attr("primary_email_field", model._primary_email);
            res.attr("partner_fields", model._mail_get_partner_fields?.());
        }
        if (request_list.includes("defaultSubject")) {
            res.attr("defaultSubject", (t) =>
                MailThread._message_compute_subject.call(this, [t.id]).get(t.id)
            );
        }
        if (request_list.includes("display_name")) {
            res.attr("display_name");
        }
        if (request_list.includes("followers")) {
            res.attr("followersCount", (t) =>
                MailFollowers.search_count([
                    ["res_id", "=", t.id],
                    ["res_model", "=", this._name],
                ])
            );
            res.one("selfFollower", "_store_follower_fields", {
                value: (t) =>
                    MailFollowers.browse(
                        MailFollowers.search([
                            ["res_id", "=", t.id],
                            ["res_model", "=", this._name],
                            ["partner_id", "=", this.env.user.partner_id],
                        ])
                    ),
            });
            this.env["mail.thread"]._store_message_followers_fields.call(this, res, {
                reset: true,
            });
            res.attr("recipientsCount", (t) =>
                MailFollowers.search_count([
                    ["res_id", "=", t.id],
                    ["res_model", "=", this._name],
                    ["partner_id", "!=", this.env.user.partner_id],
                    // subtype and partner active checks not done here for simplicity
                ])
            );
            this.env["mail.thread"]._store_message_followers_fields.call(this, res, {
                filter_recipients: true,
                reset: true,
            });
        }
        const pinned_domain = (t) => [
            ["model", "=", this._name],
            ["res_id", "=", t.id],
            ["pinned_at", "!=", false],
        ];
        if (res.is_for_internal_users() && request_list.includes("has_pinned_messages")) {
            res.attr(
                "has_pinned_messages",
                (t) => MailMessage._filter(pinned_domain(t)).length > 0
            );
        }
        if (res.is_for_internal_users() && request_list.includes("pinned_messages")) {
            res.many("pinned_messages", "_store_message_fields", {
                only_data: true,
                value: (t) => MailMessage.browse(MailMessage.search(pinned_domain(t))),
            });
        }
        if (request_list.includes("scheduledMessages")) {
            res.many("scheduledMessages", "_store_scheduled_message_fields", {
                value: (t) =>
                    MailScheduledMessage.browse(
                        MailScheduledMessage._filter([
                            ["model", "=", this._name],
                            ["res_id", "=", t.id],
                        ]).map((message) => message.id)
                    ),
            });
        }
        if (request_list.includes("suggestedRecipients")) {
            res.attr("suggestedRecipients", (t) =>
                MailThread._message_get_suggested_recipients.call(this, [t.id])
            );
        }
    }
}
