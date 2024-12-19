import { parseEmail } from "@mail/utils/common/format";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import {
    Command,
    getKwArgs,
    makeKwArgs,
    models,
    unmakeKwArgs,
} from "@web/../tests/web_test_helpers";

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
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const store = new mailDataHelpers.Store();
        MailThread._message_followers_to_store.call(
            this,
            ids,
            store,
            after,
            limit,
            filter_recipients
        );
        return store.get_result();
    }

    _message_followers_to_store(ids, store, after, limit, filter_recipients, reset) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "store",
            "after",
            "limit",
            "filter_recipients",
            "reset"
        );
        ids = kwargs.ids;
        store = kwargs.store;
        after = kwargs.after || 0;
        limit = kwargs.limit || 100;
        filter_recipients = kwargs.filter_recipients || false;
        reset = kwargs.reset || false;

        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        const domain = [
            ["res_id", "=", ids[0]],
            ["res_model", "=", this._name],
            ["partner_id", "!=", this.env.user.partner_id],
        ];
        if (after) {
            domain.push(["id", ">", after]);
        }
        if (filter_recipients) {
            // not implemented for simplicity
        }
        const followers = MailFollowers._filter(domain).sort(
            (f1, f2) => (f1.id < f2.id ? -1 : 1) // sorted from lowest ID to highest ID (i.e. from oldest to youngest)
        );
        followers.length = Math.min(followers.length, limit);
        store.add(
            this.browse(ids[0]),
            {
                [filter_recipients ? "recipients" : "followers"]: mailDataHelpers.Store.many(
                    followers,
                    reset ? "REPLACE" : "ADD"
                ),
            },
            makeKwArgs({ as_thread: true })
        );
    }

    /** @param {number[]} ids */
    message_post(ids) {
        const kwargs = getKwArgs(arguments, "ids", "subtype_id", "tracking_value_ids");
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
        const subtype_xmlid = kwargs.subtype_xmlid || "mail.mt_note";
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
        const values = unmakeKwArgs({
            ...kwargs,
            author_id,
            author_guest_id,
            email_from,
            is_discussion: subtype_xmlid === "mail.mt_comment",
            is_note: subtype_xmlid === "mail.mt_note",
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
        const store = new mailDataHelpers.Store();
        MailMessage._message_notifications_to_store(
            notifications.map((notification) => notification.mail_message_id),
            store
        );
        BusBus._sendone(partner, "mail.record/insert", store.get_result());
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
                lang,
                reason,
                create_values: {},
            });
        } else {
            const partnerCreateValues = this._get_customer_information(id);
            result.push({
                email,
                name,
                lang,
                reason,
                create_values: partnerCreateValues,
            });
        }
        return result;
    }

    _get_customer_information(id) {
        return {};
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
    _message_get_suggested_recipients(ids) {
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").ResFake} */
        const ResFake = this.env["res.fake"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        if (this._name === "res.fake") {
            return ResFake._message_get_suggested_recipients(ids);
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
                    [channel, "members"],
                    "mail.record/insert",
                    new mailDataHelpers.Store(DiscussChannel.browse(channel.id), {
                        is_pinned: true,
                    }).get_result(),
                ]);
                notifications.push([
                    channel,
                    "discuss.channel/new_message",
                    {
                        data: new mailDataHelpers.Store(
                            MailMessage.browse(message_id)
                        ).get_result(),
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
                            new mailDataHelpers.Store(
                                MailMessage.browse(message.id),
                                makeKwArgs({ for_current_user: true, add_followers: true })
                            ).get_result(),
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
            const { trackingValueIds, changedFieldNames } = tracking[record.id] || {};
            if (!changedFieldNames || !changedFieldNames.length) {
                continue;
            }
            const changedFieldsInitialValues = {};
            const initialFieldValues = initial_values_dict[record.id];
            for (const fname in changedFieldNames) {
                changedFieldsInitialValues[fname] = initialFieldValues[fname];
            }
            const subtype = MailThread._track_subtype.call(this, changedFieldsInitialValues);
            MailThread.message_post.call(this, [record.id], subtype.id, trackingValueIds);
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

    /** @param {Object} initial_values */
    _track_subtype(initial_values) {
        return false;
    }

    _thread_to_store(ids, store, fields, request_list) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields", "request_list");
        const id = kwargs.ids[0];
        store = kwargs.store;
        fields = kwargs.fields;
        request_list = kwargs.request_list;

        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailActivity} */
        const MailActivity = this.env["mail.activity"];
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").MailScheduledMessage} */
        const MailScheduledMessage = this.env["mail.scheduled.message"];

        if (!fields) {
            fields = [];
        }
        const [thread] = this.env[this._name].browse(id);
        const [res] = this._read_format(thread.id, fields, false);
        if (request_list) {
            res.hasReadAccess = true;
            res.hasWriteAccess = thread.hasWriteAccess ?? true; // mimic user with write access by default
            res["canPostOnReadonly"] = this._mail_post_access === "read";
        }
        if (request_list && request_list.includes("activities") && this.has_activities) {
            res["activities"] = mailDataHelpers.Store.many(
                MailActivity.browse(thread.activity_ids)
            );
        }
        if (request_list && request_list.includes("attachments")) {
            res["attachments"] = mailDataHelpers.Store.many(
                IrAttachment._filter([
                    ["res_id", "=", thread.id],
                    ["res_model", "=", this._name],
                ]).sort((a1, a2) => a1.id - a2.id)
            );
            res["areAttachmentsLoaded"] = true;
            res["isLoadingAttachments"] = false;
            // Specific implementation of mail.thread.main.attachment
            if (this.env[this._name]._fields.message_main_attachment_id) {
                res["mainAttachment"] = mailDataHelpers.Store.one(
                    IrAttachment.browse(thread.message_main_attachment_id),
                    makeKwArgs({ only_id: true })
                );
            }
        }
        if (fields.includes("display_name")) {
            res.name = thread.display_name ?? thread.name;
        }
        if (request_list && request_list.includes("followers")) {
            res["followersCount"] = this.env["mail.followers"].search_count([
                ["res_id", "=", thread.id],
                ["res_model", "=", this._name],
            ]);
            res["selfFollower"] = mailDataHelpers.Store.one(
                MailFollowers.browse(
                    MailFollowers.search([
                        ["res_id", "=", thread.id],
                        ["res_model", "=", this._name],
                        ["partner_id", "=", this.env.user.partner_id],
                    ])
                )
            );
            MailThread._message_followers_to_store.call(
                this,
                [id],
                store,
                makeKwArgs({ reset: true })
            );
            res["recipientsCount"] = this.env["mail.followers"].search_count([
                ["res_id", "=", thread.id],
                ["res_model", "=", this._name],
                ["partner_id", "!=", this.env.user.partner_id],
                // subtype and partner active checks not done here for simplicity
            ]);
            MailThread._message_followers_to_store.call(
                this,
                [id],
                store,
                makeKwArgs({ filter_recipients: true, reset: true })
            );
        }
        if (fields.includes("modelName")) {
            res.modelName = this._description;
        }
        if (request_list && request_list.includes("suggestedRecipients")) {
            res["suggestedRecipients"] = MailThread._message_get_suggested_recipients.call(this, [
                id,
            ]);
        }
        if (request_list && request_list.includes("scheduledMessages")) {
            res["scheduledMessages"] = mailDataHelpers.Store.many(
                MailScheduledMessage.filter(
                    (message) => message.model === this._name && message.res_id === id
                )
            );
        }
        store.add(this.env[this._name].browse(id), res, makeKwArgs({ as_thread: true }));
    }
}
