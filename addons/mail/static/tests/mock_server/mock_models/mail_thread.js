/** @odoo-module */

import { Command, constants, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";

/**
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 */

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

export class MailThread extends models.ServerModel {
    _name = "mail.thread";

    /**
     * @param {number[]} ids
     * @param {number} [after]
     * @param {number} [limit=100]
     * @param {KwArgs<{ after: number[]; limit: number }>} [kwargs]
     */
    message_get_followers(ids, after, limit, kwargs = {}) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        after = kwargs.after || after || 0;
        limit = kwargs.limit || limit || 100;
        const modelName = kwargs.model || this._name;
        const domain = [
            ["res_id", "=", ids[0]],
            ["res_model", "=", modelName],
        ];
        if (after) {
            domain.push(["id", ">", after]);
        }
        if (kwargs.filter_recipients) {
            domain.push(["partner_id", "!=", constants.PARTNER_ID]);
        }
        const followers = MailFollowers._filter(domain).sort(
            (f1, f2) => (f1.id < f2.id ? -1 : 1) // sorted from lowest ID to highest ID (i.e. from oldest to youngest)
        );
        followers.length = Math.min(followers.length, limit);
        return MailFollowers._format_for_chatter(followers.map((follower) => follower.id));
    }

    /**
     * @param {number[]} ids
     * @param {KwArgs<{ attachment_ids: number[]; partner_ids: number[] }>} [kwargs]
     */
    message_post(ids, kwargs = {}) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const { model } = kwargs;
        const id = ids[0]; // ensure_one
        if (kwargs.context?.mail_post_autofollow && kwargs.partner_ids?.length) {
            this.message_subscribe(ids, kwargs.partner_ids, [], [], { model });
        }
        if (kwargs.attachment_ids) {
            const attachments = IrAttachment._filter([
                ["id", "in", kwargs.attachment_ids],
                ["res_model", "=", "mail.compose.message"],
                ["res_id", "=", 0],
            ]);
            const attachmentIds = attachments.map((attachment) => attachment.id);
            IrAttachment.write(attachmentIds, {
                res_id: id,
                res_model: model,
            });
            kwargs.attachment_ids = attachmentIds.map((attachmentId) => Command.link(attachmentId));
        }
        const subtype_xmlid = kwargs.subtype_xmlid || "mail.mt_note";
        const authorGuestId = this.env.user?.is_public && MailGuest._get_guest_from_context()?.id;
        let authorId;
        let emailFrom;
        if (!authorGuestId) {
            [authorId, emailFrom] = this._message_compute_author(
                kwargs.author_id,
                kwargs.email_from
            );
        }

        const values = {
            ...kwargs,
            author_id: authorId,
            author_guest_id: authorGuestId,
            email_from: emailFrom,
            is_discussion: subtype_xmlid === "mail.mt_comment",
            is_note: subtype_xmlid === "mail.mt_note",
            model,
            res_id: id,
        };
        delete values.context;
        delete values.subtype_xmlid;
        const messageId = MailMessage.create(values);
        this._notify_thread(model, ids, messageId, kwargs.context?.temporary_id);
        return {
            ...MailMessage.message_format([messageId])[0],
            temporary_id: kwargs.context?.temporary_id,
        };
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partnerIds
     * @param {number[]} subTypeIds
     * @param {KwArgs<{ partner_ids: number[]; subtype_ids: number[] }>} [kwargs]
     */
    message_subscribe(ids, partnerIds, subTypeIds, kwargs = {}) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        partnerIds = kwargs.partner_ids || partnerIds || [];
        subTypeIds = kwargs.subtype_ids || subTypeIds || [];
        const modelName = kwargs.model || this._name;
        for (const id of ids) {
            for (const partner_id of partnerIds) {
                let followerId = MailFollowers.search([["partner_id", "=", partner_id]])[0];
                if (!followerId) {
                    if (!subTypeIds?.length) {
                        subTypeIds = MailMessageSubtype.search([
                            ["default", "=", true],
                            "|",
                            ["res_model", "=", modelName],
                            ["res_model", "=", false],
                        ]);
                    }
                    followerId = MailFollowers.create({
                        is_active: true,
                        partner_id,
                        res_id: id,
                        res_model: modelName,
                        subtype_ids: subTypeIds,
                    });
                }
                this.env[modelName].write(ids, { message_follower_ids: [followerId] });
                ResPartner.write([partner_id], { message_follower_ids: [followerId] });
            }
        }
    }

    /**
     * @param {number[]} ids
     * @param {number[]} partnerIds
     * @param {KwArgs<{ partner_ids: number[] }>} [kwargs]
     */
    message_unsubscribe(ids, partnerIds, kwargs = {}) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        partnerIds = kwargs.partner_ids || partnerIds || [];
        if (!partnerIds.length) {
            return true;
        }
        const followers = MailFollowers._filter([
            ["res_model", "=", kwargs.model || this._name],
            ["res_id", "in", ids],
            ["partner_id", "in", partnerIds],
        ]);
        MailFollowers.unlink(followers.map((follower) => follower.id));
    }

    /**
     * Note that this method is overridden by snailmail module but not simulated here.
     *
     * @param {string} notificationType
     * @param {KwArgs<{ notification_type: string }>} [kwargs]
     */
    notify_cancel_by_type(notificationType, kwargs = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        notificationType = kwargs.notification_type || notificationType;
        const modelName = kwargs.model || this._name;
        // Query matching notifications
        const notifications = MailNotification._filter([
            ["notification_type", "=", notificationType],
            ["notification_status", "in", ["bounce", "exception"]],
        ]).filter((notification) => {
            const message = MailMessage._filter([["id", "=", notification.mail_message_id]])[0];
            return message.model === modelName && message.author_id === constants.PARTNER_ID;
        });
        // Update notification status
        MailNotification.write(
            notifications.map((notification) => notification.id),
            { notification_status: "canceled" }
        );
        // Send bus notifications to update status of notifications in the web client
        const [partner] = ResPartner.read(constants.PARTNER_ID);
        BusBus._sendone(partner, "mail.message/notification_update", {
            elements: MailMessage._message_notification_format(
                notifications.map((notification) => notification.mail_message_id)
            ),
        });
    }

    /**
     * @param {string} model
     * @param {Object} result
     * @param {{ email: string; partner: number; reason: string  }} [params]
     */
    _message_add_suggested_recipient(model, result, { email, partner, reason = "" } = {}) {
        const record = this.env[model]._filter([["id", "in", "ids"]])[0];
        // for simplicity
        result[record.id].push([partner, email, reason]);
        return result;
    }

    /**
     * @param {number} [author_id]
     * @param {string} [emailFrom]
     */
    _message_compute_author(authorId, emailFrom) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (!authorId) {
            // For simplicity partner is not guessed from email_from here, but
            // that would be the first step on the server.
            const author = ResPartner._filter([["id", "=", constants.PARTNER_ID]], {
                active_test: false,
            })[0];
            authorId = author.id;
            emailFrom = `${author.display_name} <${author.email}>`;
        }

        if (!emailFrom && authorId) {
            const author = ResPartner._filter([["id", "=", authorId]], {
                active_test: false,
            })[0];
            emailFrom = `${author.display_name} <${author.email}>`;
        }

        if (!emailFrom) {
            throw Error("Unable to log message due to missing author email.");
        }

        return [authorId, emailFrom];
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     */
    _message_compute_subject(model, ids) {
        const records = this.env[model]._filter([["id", "in", ids]]);
        return new Map(records.map((record) => [record.id, record.name || ""]));
    }

    /**
     * @param {string} modelName
     * @param {number[]} ids
     */
    _message_get_suggested_recipients(modelName, ids) {
        /** @type {import("mock_models").ResFake} */
        const ResFake = this.env["res.fake"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        if (modelName === "res.fake") {
            return ResFake._message_get_suggested_recipients(modelName, ids);
        }
        const result = ids.reduce((result, id) => (result[id] = []), {});
        const model = this.env[modelName];
        for (const record in model._filter([["id", "in", ids]])) {
            if (record.user_id) {
                const user = ResUsers._filter([["id", "=", record.user_id]]);
                if (user.partner_id) {
                    const reason = model._fields["user_id"].string;
                    this._message_add_suggested_recipient(modelName, result, {
                        partner: user.partner_id,
                        reason,
                    });
                }
            }
        }
        return result;
    }

    /**
     * Simplified version that sends notification to author and channel.
     *
     * @param {string} modelName
     * @param {number[]} ids
     * @param {number} messageId
     * @param {number} [temporaryId]
     */
    _notify_thread(modelName, ids, messageId, temporaryId) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const message = MailMessage._filter([["id", "=", messageId]])[0];
        const messageFormat = MailMessage.message_format([messageId])[0];
        const notifications = [];
        if (modelName === "discuss.channel") {
            // members
            const channels = DiscussChannel._filter([["id", "=", message.res_id]]);
            for (const channel of channels) {
                // notify update of last_interest_dt
                const now = serializeDateTime(today());
                const members = DiscussChannelMember._filter([
                    ["id", "in", channel.channel_member_ids],
                ]);
                DiscussChannelMember.write(
                    members.map((member) => member.id),
                    { last_interest_dt: now }
                );
                for (const member of members) {
                    const target = member.guest_id
                        ? MailGuest.search_read([["id", "=", member.guest_id]])[0]
                        : ResPartner.search_read([["id", "=", member.partner_id]], {
                              context: { active_test: false },
                          })[0];
                    notifications.push([
                        target,
                        "discuss.channel/last_interest_dt_changed",
                        {
                            id: channel.id,
                            isServerPinned: member.is_pinned,
                            last_interest_dt: member.last_interest_dt,
                        },
                    ]);
                }
                notifications.push([
                    channel,
                    "discuss.channel/new_message",
                    {
                        id: channel.id,
                        message: Object.assign(messageFormat, { temporary_id: temporaryId }),
                    },
                ]);
                if (message.author_id === constants.PARTNER_ID) {
                    DiscussChannel._channel_seen(ids, message.id);
                }
            }
        }
        BusBus._sendmany(notifications);
    }

    /**
     * @param {string} modelName
     * @param {string[]} trackedFieldNames
     * @param {Object} initialTrackedFieldValuesByRecordId
     */
    _message_track(modelName, trackedFieldNames, initialTrackedFieldValuesByRecordId) {
        /** @type {import("mock_models").Base} */
        const Base = this.env["base"];

        const trackFieldNamesToField = this.env[modelName].fields_get(trackedFieldNames);
        const tracking = {};
        const model = this.env[modelName];
        for (const record of model) {
            tracking[record.id] = Base._mail_track(
                modelName,
                trackFieldNamesToField,
                initialTrackedFieldValuesByRecordId[record.id],
                record
            );
        }
        for (const record of model) {
            const { trackingValueIds, changedFieldNames } = tracking[record.id] || {};
            if (!changedFieldNames || !changedFieldNames.length) {
                continue;
            }
            const changedFieldsInitialValues = {};
            const initialFieldValues = initialTrackedFieldValuesByRecordId[record.id];
            for (const fname in changedFieldNames) {
                changedFieldsInitialValues[fname] = initialFieldValues[fname];
            }
            const subtype = this._track_subtype(changedFieldsInitialValues);
            this.message_post([record.id], {
                model: modelName,
                subtype_id: subtype.id,
                tracking_value_ids: trackingValueIds,
            });
        }
        return tracking;
    }

    /**
     * @param {string} modelName
     * @param {string[]} trackedFieldNames
     * @param {Object} initialTrackedFieldValuesByRecordId
     */
    _track_finalize(model, initialTrackedFieldValuesByRecordId) {
        this._message_track(
            model,
            this._track_get_fields(model),
            initialTrackedFieldValuesByRecordId
        );
    }

    /** @param {string} modelName */
    _track_get_fields(model) {
        return Object.entries(this.env[model]._fields).reduce((prev, next) => {
            if (next[1].tracking) {
                prev.push(next[0]);
            }
            return prev;
        }, []);
    }

    /** @param {string} modelName */
    _track_prepare(modelName) {
        const trackedFieldNames = this._track_get_fields(modelName);
        if (!trackedFieldNames.length) {
            return;
        }
        const initialTrackedFieldValuesByRecordId = {};
        for (const record of this.env[modelName]) {
            const values = {};
            initialTrackedFieldValuesByRecordId[record.id] = values;
            for (const fname of trackedFieldNames) {
                values[fname] = record[fname];
            }
        }
        return initialTrackedFieldValuesByRecordId;
    }

    /** @param {Object} initialFieldValuesByRecordId */
    _track_subtype(initialFieldValuesByRecordId) {
        return false;
    }

    _get_mail_thread_data(model, id, request_list) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailActivity} */
        const MailActivity = this.env["mail.activity"];
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];

        const res = {
            hasWriteAccess: true, // mimic user with write access by default
            hasReadAccess: true,
        };
        const thread = this.env[model].search_read([["id", "=", id]])[0];
        if (!thread) {
            res["hasReadAccess"] = false;
            return res;
        }
        res["canPostOnReadonly"] = model === "discuss.channel"; // model that have attr _mail_post_access='read'
        if (request_list.includes("activities")) {
            const activities = MailActivity.search_read([["id", "in", thread.activity_ids || []]]);
            res["activities"] = MailActivity.activity_format(
                activities.map((activity) => activity.id)
            );
        }
        if (request_list.includes("attachments")) {
            const attachments = IrAttachment.search_read([
                ["res_id", "=", thread.id],
                ["res_model", "=", model],
            ]); // order not done for simplicity
            res["attachments"] = IrAttachment._attachment_format(
                attachments.map((attachment) => attachment.id)
            );
            // Specific implementation of mail.thread.main.attachment
            if (this.env[model]._fields.message_main_attachment_id) {
                res["mainAttachment"] = thread.message_main_attachment_id
                    ? { id: thread.message_main_attachment_id[0] }
                    : false;
            }
        }
        if (request_list.includes("followers")) {
            const domain = [
                ["res_id", "=", thread.id],
                ["res_model", "=", model],
            ];
            res["followersCount"] = (thread.message_follower_ids || []).length;
            const selfFollower = MailFollowers.search_read(
                domain.concat([["partner_id", "=", constants.PARTNER_ID]])
            )[0];
            res["selfFollower"] = selfFollower
                ? MailFollowers._format_for_chatter(selfFollower.id)[0]
                : false;
            res["followers"] = this.message_get_followers(model, [id]);
            res["recipientsCount"] = (thread.message_follower_ids || []).length - 1;
            res["recipients"] = this.message_get_followers(model, [id], undefined, 100, {
                filter_recipients: true,
            });
        }
        if (request_list.includes("suggestedRecipients")) {
            res["suggestedRecipients"] = this._message_get_suggested_recipients(model, [thread.id])[
                id
            ];
        }
        return res;
    }
}
