/** @odoo-module */

import { Command, models } from "@web/../tests/web_test_helpers";
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
     * Simulates `message_get_followers` on `mail.thread`.
     *
     * @param {number[]} ids
     * @param {number} [after]
     * @param {number} [limit=100]
     * @param {KwArgs<{ after: number[]; limit: number }>} [kwargs]
     */
    message_get_followers(ids, after, limit, kwargs = {}) {
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
            domain.push(["partner_id", "!=", this.env.partner_id]);
        }
        const followers = this.env["mail.followers"]._filter(domain).sort(
            (f1, f2) => (f1.id < f2.id ? -1 : 1) // sorted from lowest ID to highest ID (i.e. from oldest to youngest)
        );
        followers.length = Math.min(followers.length, limit);
        return this.env["mail.followers"]._formatForChatter(
            followers.map((follower) => follower.id)
        );
    }

    /**
     * Simulates `message_post` on `mail.thread`.
     *
     * @param {number[]} ids
     * @param {KwArgs<{ attachment_ids: number[]; partner_ids: number[] }>} [kwargs]
     */
    message_post(ids, kwargs = {}) {
        const { model } = kwargs;
        const id = ids[0]; // ensure_one
        if (kwargs.context?.mail_post_autofollow && kwargs.partner_ids?.length) {
            this.message_subscribe(ids, kwargs.partner_ids, [], [], { model });
        }
        if (kwargs.attachment_ids) {
            const attachments = this.env["ir.attachment"]._filter([
                ["id", "in", kwargs.attachment_ids],
                ["res_model", "=", "mail.compose.message"],
                ["res_id", "=", 0],
            ]);
            const attachmentIds = attachments.map((attachment) => attachment.id);
            this.env["ir.attachment"].write(attachmentIds, {
                res_id: id,
                res_model: model,
            });
            kwargs.attachment_ids = attachmentIds.map((attachmentId) => Command.link(attachmentId));
        }
        const subtype_xmlid = kwargs.subtype_xmlid || "mail.mt_note";
        const authorGuestId =
            this.env.user?.is_public && this.env["mail.guest"]._getGuestFromContext()?.id;
        let authorId;
        let emailFrom;
        if (!authorGuestId) {
            [authorId, emailFrom] = this._messageComputeAuthor(kwargs.author_id, kwargs.email_from);
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
        const messageId = this.env["mail.message"].create(values);
        this._notifyThread(model, ids, messageId, kwargs.context?.temporary_id);
        return {
            ...this.env["mail.message"].message_format([messageId])[0],
            temporary_id: kwargs.context?.temporary_id,
        };
    }

    /**
     * Simulates `message_subscribe` on `mail.thread`.
     *
     * @param {number[]} ids
     * @param {number[]} partnerIds
     * @param {number[]} subTypeIds
     * @param {KwArgs<{ partner_ids: number[]; subtype_ids: number[] }>} [kwargs]
     */
    message_subscribe(ids, partnerIds, subTypeIds, kwargs = {}) {
        partnerIds = kwargs.partner_ids || partnerIds || [];
        subTypeIds = kwargs.subtype_ids || subTypeIds || [];
        const modelName = kwargs.model || this._name;
        for (const id of ids) {
            for (const partner_id of partnerIds) {
                let followerId = this.env["mail.followers"].search([
                    ["partner_id", "=", partner_id],
                ])[0];
                if (!followerId) {
                    if (!subTypeIds?.length) {
                        subTypeIds = this.env["mail.message.subtype"].search([
                            ["default", "=", true],
                            "|",
                            ["res_model", "=", modelName],
                            ["res_model", "=", false],
                        ]);
                    }
                    followerId = this.env["mail.followers"].create({
                        is_active: true,
                        partner_id,
                        res_id: id,
                        res_model: modelName,
                        subtype_ids: subTypeIds,
                    });
                }
                this.env[modelName].write(ids, { message_follower_ids: [followerId] });
                this.env["res.partner"].write([partner_id], {
                    message_follower_ids: [followerId],
                });
            }
        }
    }

    /**
     * Simulates `message_unsubscribe` on `mail.thread`.
     *
     * @param {number[]} ids
     * @param {number[]} partnerIds
     * @param {KwArgs<{ partner_ids: number[] }>} [kwargs]
     */
    message_unsubscribe(ids, partnerIds, kwargs = {}) {
        partnerIds = kwargs.partner_ids || partnerIds || [];
        if (!partnerIds.length) {
            return true;
        }
        const followers = this.env["mail.followers"]._filter([
            ["res_model", "=", kwargs.model || this._name],
            ["res_id", "in", ids],
            ["partner_id", "in", partnerIds],
        ]);
        this.env["mail.followers"].unlink(followers.map((follower) => follower.id));
    }

    /**
     * Simulate the `notify_cancel_by_type` on `mail.thread` .
     * Note that this method is overridden by snailmail module but not simulated here.
     *
     * @param {string} notificationType
     * @param {KwArgs<{ notification_type: string }>} [kwargs]
     */
    notify_cancel_by_type(notificationType, kwargs = {}) {
        notificationType = kwargs.notification_type || notificationType;
        const modelName = kwargs.model || this._name;
        // Query matching notifications
        const notifications = this.env["mail.notification"]
            ._filter([
                ["notification_type", "=", notificationType],
                ["notification_status", "in", ["bounce", "exception"]],
            ])
            .filter((notification) => {
                const message = this.env["mail.message"]._filter([
                    ["id", "=", notification.mail_message_id],
                ])[0];
                return message.model === modelName && message.author_id === this.env.partner_id;
            });
        // Update notification status
        this.env["mail.notification"].write(
            notifications.map((notification) => notification.id),
            { notification_status: "canceled" }
        );
        // Send bus notifications to update status of notifications in the web client
        this.env["bus.bus"]._sendone(this.env.partner, "mail.message/notification_update", {
            elements: this.env["mail.message"]._messageNotificationFormat(
                notifications.map((notification) => notification.mail_message_id)
            ),
        });
    }

    /**
     * Simulates `_message_add_suggested_recipient` on `mail.thread`.
     *
     * @param {string} model
     * @param {Object} result
     * @param {{ email: string; partner: number; reason: string  }} [params]
     */
    _messageAddSuggestedRecipient(model, result, { email, partner, reason = "" } = {}) {
        const record = this.env[model]._filter([["id", "in", "ids"]])[0];
        // for simplicity
        result[record.id].push([partner, email, reason]);
        return result;
    }

    /**
     * Simulates `_message_compute_author` on `mail.thread`.
     *
     * @param {number} [author_id]
     * @param {string} [emailFrom]
     */
    _messageComputeAuthor(authorId, emailFrom) {
        if (!authorId) {
            // For simplicity partner is not guessed from email_from here, but
            // that would be the first step on the server.
            const author = this.env["res.partner"]._filter([["id", "=", this.env.partner_id]], {
                active_test: false,
            })[0];
            authorId = author.id;
            emailFrom = `${author.display_name} <${author.email}>`;
        }

        if (!emailFrom && authorId) {
            const author = this.env["res.partner"]._filter([["id", "=", authorId]], {
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
     * Simulate `_message_compute_subject` on `mail.thread`.
     *
     * @param {string} model
     * @param {number[]} ids
     */
    _messageComputeSubject(model, ids) {
        const records = this.env[model]._filter([["id", "in", ids]]);
        return new Map(records.map((record) => [record.id, record.name || ""]));
    }

    /**
     * Simulates `_message_get_suggested_recipients` on `mail.thread`.
     *
     * @param {string} modelName
     * @param {number[]} ids
     */
    _messageGetSuggestedRecipients(modelName, ids) {
        if (modelName === "res.fake") {
            return this.env["res.fake"]._messageGetSuggestedRecipients(modelName, ids);
        }
        const result = ids.reduce((result, id) => (result[id] = []), {});
        const model = this.env[modelName];
        for (const record in model._filter([["id", "in", ids]])) {
            if (record.user_id) {
                const user = this.env["res.users"]._filter([["id", "=", record.user_id]]);
                if (user.partner_id) {
                    const reason = model._fields["user_id"].string;
                    this._messageAddSuggestedRecipient(modelName, result, {
                        partner: user.partner_id,
                        reason,
                    });
                }
            }
        }
        return result;
    }

    /**
     * Simulates `_notify_thread` on `mail.thread`.
     * Simplified version that sends notification to author and channel.
     *
     * @param {string} modelName
     * @param {number[]} ids
     * @param {number} messageId
     * @param {number} [temporaryId]
     */
    _notifyThread(modelName, ids, messageId, temporaryId) {
        const message = this.env["mail.message"]._filter([["id", "=", messageId]])[0];
        const messageFormat = this.env["mail.message"].message_format([messageId])[0];
        const notifications = [];
        if (modelName === "discuss.channel") {
            // members
            const channels = this.env["discuss.channel"]._filter([["id", "=", message.res_id]]);
            for (const channel of channels) {
                // notify update of last_interest_dt
                const now = serializeDateTime(today());
                const members = this.env["discuss.channel.member"]._filter([
                    ["id", "in", channel.channel_member_ids],
                ]);
                this.env["discuss.channel.member"].write(
                    members.map((member) => member.id),
                    { last_interest_dt: now }
                );
                for (const member of members) {
                    const target = member.guest_id
                        ? this.env["mail.guest"].search_read([["id", "=", member.guest_id]])[0]
                        : this.env["res.partner"].search_read([["id", "=", member.partner_id]], {
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
                if (message.author_id === this.env.partner_id) {
                    this.env["discuss.channel"]._channelSeen(ids, message.id);
                }
            }
        }
        this.env["bus.bus"]._sendmany(notifications);
    }

    /**
     * Simulates `_message_track` on `mail.thread`.
     *
     * @param {string} modelName
     * @param {string[]} trackedFieldNames
     * @param {Object} initialTrackedFieldValuesByRecordId
     */
    _messageTrack(modelName, trackedFieldNames, initialTrackedFieldValuesByRecordId) {
        const trackFieldNamesToField = this.env[modelName].fields_get(trackedFieldNames);
        const tracking = {};
        const model = this.env[modelName];
        for (const record of model) {
            tracking[record.id] = this.env["base"]._mailTrack(
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
            const subtype = this._trackSubtype(changedFieldsInitialValues);
            this.message_post([record.id], {
                model: modelName,
                subtype_id: subtype.id,
                tracking_value_ids: trackingValueIds,
            });
        }
        return tracking;
    }

    /**
     * Simulates `_track_finalize` on `mail.thread`.
     *
     * @param {string} modelName
     * @param {string[]} trackedFieldNames
     * @param {Object} initialTrackedFieldValuesByRecordId
     */
    _trackFinalize(model, initialTrackedFieldValuesByRecordId) {
        this._messageTrack(model, this._trackGetFields(model), initialTrackedFieldValuesByRecordId);
    }

    /**
     * Simulates `_track_get_fields` on `mail.thread`.
     *
     * @param {string} modelName
     */
    _trackGetFields(model) {
        return Object.entries(this.env[model]._fields).reduce((prev, next) => {
            if (next[1].tracking) {
                prev.push(next[0]);
            }
            return prev;
        }, []);
    }

    /**
     * Simulates `_track_prepare` on `mail.thread`.
     *
     * @param {string} modelName
     */
    _trackPrepare(modelName) {
        const trackedFieldNames = this._trackGetFields(modelName);
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

    /**
     * Simulates `_track_subtype` on `mail.thread`.
     *
     * @param {Object} initialFieldValuesByRecordId
     */
    _trackSubtype(initialFieldValuesByRecordId) {
        return false;
    }
}
