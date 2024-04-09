import { parseEmail } from "@mail/utils/common/format";
import { Command, models } from "@web/../tests/web_test_helpers";
import { parseModelParams } from "../mail_mock_server";
import { Kwargs } from "@web/../tests/_framework/mock_server/mock_server_utils";

export class MailThread extends models.ServerModel {
    _name = "mail.thread";
    _inherit = ["base"];

    /**
     * @param {number[]} ids
     * @param {number} [after]
     * @param {number} [limit=100]
     * @param {boolean} [filter_recipients]
     */
    message_get_followers(ids, after, limit = 100, filter_recipients) {
        const kwargs = parseModelParams(arguments, "ids", "after", "limit");
        ids = kwargs.ids;
        delete kwargs.ids;
        after = kwargs.after || 0;
        limit = kwargs.limit || 100;
        filter_recipients = kwargs.filter_recipients;

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
            domain.push(["partner_id", "!=", this.env.user.partner_id]);
        }
        const followers = MailFollowers._filter(domain).sort(
            (f1, f2) => (f1.id < f2.id ? -1 : 1) // sorted from lowest ID to highest ID (i.e. from oldest to youngest)
        );
        followers.length = Math.min(followers.length, limit);
        return MailFollowers._format_for_chatter(followers.map((follower) => follower.id));
    }

    /** @param {number[]} ids */
    message_post(ids) {
        const kwargs = parseModelParams(arguments, "ids");
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
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const id = ids[0]; // ensure_one
        if (kwargs.partner_emails) {
            kwargs.partner_ids = kwargs.partner_ids || [];
            for (const email of kwargs.partner_emails) {
                const partner = ResPartner._filter([["email", "=", email]]);
                if (partner.length !== 0) {
                    kwargs.partner_ids.push(partner[0].id);
                } else {
                    const partner_id = ResPartner.create(
                        Object.assign({ email }, kwargs.partner_additional_values[email] || {})
                    );
                    kwargs.partner_ids.push(partner_id);
                }
            }
        }
        delete kwargs.partner_emails;
        delete kwargs.partner_additional_values;
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
        const values = {
            ...kwargs,
            author_id,
            author_guest_id,
            email_from,
            is_discussion: subtype_xmlid === "mail.mt_comment",
            is_note: subtype_xmlid === "mail.mt_note",
            model: this._name,
            res_id: id,
        };
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
        return {
            ...MailMessage._message_format([messageId])[0],
            temporary_id: kwargs.context?.temporary_id,
        };
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partner_ids
     * @param {number[]} subtype_ids
     */
    message_subscribe(ids, partner_ids, subtype_ids) {
        const kwargs = parseModelParams(arguments, "ids", "partner_ids", "subtype_ids");
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
        const kwargs = parseModelParams(arguments, "ids", "partner_ids");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];

        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        if (!partner_ids.length) {
            return true;
        }
        const followers = MailFollowers._filter([
            ["res_model", "=", this._name],
            ["res_id", "in", ids],
            ["partner_id", "in", partner_ids],
        ]);
        MailFollowers.unlink(followers.map((follower) => follower.id));
    }

    /**
     * Note that this method is overridden by snailmail module but not simulated here.
     *
     * @param {string} notification_type
     */
    notify_cancel_by_type(notification_type) {
        const kwargs = parseModelParams(arguments, "notification_type");
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
            const message = MailMessage._filter([["id", "=", notification.mail_message_id]])[0];
            return message.model === this._name && message.author_id === this.env.user.partner_id;
        });
        // Update notification status
        MailNotification.write(
            notifications.map((notification) => notification.id),
            { notification_status: "canceled" }
        );
        // Send bus notifications to update status of notifications in the web client
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "mail.message/notification_update", {
            elements: MailMessage._message_notification_format(
                notifications.map((notification) => notification.mail_message_id)
            ),
        });
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
        const kwargs = parseModelParams(
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

        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
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
            const partnerCreateValues = MailThread._get_customer_information.call(this, id);
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
        const kwargs = parseModelParams(arguments, "author_id", "email_from");
        author_id = kwargs.author_id;
        email_from = kwargs.email_from;

        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (!author_id) {
            // For simplicity partner is not guessed from email_from here, but
            // that would be the first step on the server.
            const author = ResPartner._filter([["id", "=", this.env.user.partner_id]], {
                active_test: false,
            })[0];
            author_id = author.id;
            email_from = `${author.display_name} <${author.email}>`;
        }
        if (!email_from && author_id) {
            const author = ResPartner._filter([["id", "=", author_id]], {
                active_test: false,
            })[0];
            email_from = `${author.display_name} <${author.email}>`;
        }
        if (email_from === undefined) {
            if (author_id) {
                const author = ResPartner._filter([["id", "=", author_id]], {
                    active_test: false,
                })[0];
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
        const records = this._filter([["id", "in", ids]]);
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
        for (const record in model._filter([["id", "in", ids]])) {
            if (record.user_id) {
                const user = ResUsers._filter([["id", "=", record.user_id]]);
                if (user.partner_id) {
                    const reason = model._fields["user_id"].string;
                    const partner = ResPartner._filter([["id", "=", user.partner_id]]);
                    MailThread._message_add_suggested_recipient.call(
                        this,
                        result,
                        Kwargs({
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
        const kwargs = parseModelParams(arguments, "ids", "message_id", "temporary_id");
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

        const message = MailMessage._filter([["id", "=", message_id]])[0];
        const messageFormat = MailMessage._message_format([message_id])[0];
        const notifications = [];
        if (this._name === "discuss.channel") {
            // members
            const channels = DiscussChannel._filter([["id", "=", message.res_id]]);
            for (const channel of channels) {
                notifications.push([
                    [channel, "members"],
                    "mail.record/insert",
                    {
                        Thread: {
                            id: channel.id,
                            is_pinned: true,
                            model: "discuss.channel",
                        },
                    },
                ]);
                notifications.push([
                    channel,
                    "discuss.channel/new_message",
                    {
                        id: channel.id,
                        message: Object.assign(messageFormat, { temporary_id }),
                    },
                ]);
                if (message.author_id === this.env.user?.partner_id) {
                    DiscussChannel._channel_seen(ids, message.id);
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
        const kwargs = parseModelParams(arguments, "fields_iter", "initial_values_dict");
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
            MailThread.message_post.call(this, [record.id], {
                subtype_id: subtype.id,
                tracking_value_ids: trackingValueIds,
            });
        }
        return tracking;
    }

    /** @param {Object} initial_values */
    _track_finalize(initial_values) {
        const kwargs = parseModelParams(arguments, "initial_values");
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

    _get_mail_thread_data(id, request_list) {
        const kwargs = parseModelParams(arguments, "id", "request_list");
        id = kwargs.id;
        delete kwargs.id;
        request_list = kwargs.request_list;

        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailActivity} */
        const MailActivity = this.env["mail.activity"];
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const res = {
            hasWriteAccess: true, // mimic user with write access by default
            hasReadAccess: true,
            id,
            model: this._name,
        };
        const thread = this.env[this._name].search_read([["id", "=", id]])[0];
        if (!thread) {
            res["hasReadAccess"] = false;
            return res;
        }
        res["canPostOnReadonly"] = this._name === "discuss.channel"; // model that have attr _mail_post_access='read'
        if (this.has_activities) {
            const activities = MailActivity.search_read([["id", "in", thread.activity_ids || []]]);
            res["activities"] = MailActivity.activity_format(
                activities.map((activity) => activity.id)
            );
        }
        if (request_list.includes("attachments")) {
            const attachments = IrAttachment.search_read([
                ["res_id", "=", thread.id],
                ["res_model", "=", this._name],
            ]); // order not done for simplicity
            res["attachments"] = IrAttachment._attachment_format(
                attachments.map((attachment) => attachment.id)
            );
            // Specific implementation of mail.thread.main.attachment
            if (this.env[this._name]._fields.message_main_attachment_id) {
                res["mainAttachment"] = thread.message_main_attachment_id
                    ? { id: thread.message_main_attachment_id[0] }
                    : false;
            }
        }
        if (request_list.includes("followers")) {
            const domain = [
                ["res_id", "=", thread.id],
                ["res_model", "=", this._name],
            ];
            res["followersCount"] = (thread.message_follower_ids || []).length;
            const selfFollower = MailFollowers.search_read(
                domain.concat([["partner_id", "=", this.env.user.partner_id]])
            )[0];
            res["selfFollower"] = selfFollower
                ? MailFollowers._format_for_chatter(selfFollower.id)[0]
                : false;
            res["followers"] = MailThread.message_get_followers.call(this, [id]);
            res["recipientsCount"] = (thread.message_follower_ids || []).length - 1;
            res["recipients"] = MailThread.message_get_followers.call(
                this,
                [id],
                undefined,
                100,
                Kwargs({ filter_recipients: true })
            );
        }
        if (request_list.includes("suggestedRecipients")) {
            res["suggestedRecipients"] = MailThread._message_get_suggested_recipients.call(this, [
                id,
            ]);
        }
        return res;
    }
}
