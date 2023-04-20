/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

import { datetime_to_str } from "web.time";

patch(MockServer.prototype, "mail/models/mail_thread", {
    async _performRPC(route, args) {
        if (args.method === "message_subscribe") {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            const subtype_ids = args.args[2] || args.kwargs.subtype_ids;
            return this._mockMailThreadMessageSubscribe(args.model, ids, partner_ids, subtype_ids);
        }
        if (args.method === "message_unsubscribe") {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            return this._mockMailThreadMessageUnsubscribe(args.model, ids, partner_ids);
        }
        if (args.method === "message_post") {
            const id = args.args[0];
            const kwargs = args.kwargs;
            const context = kwargs.context;
            delete kwargs.context;
            return this._mockMailThreadMessagePost(args.model, [id], kwargs, context);
        }
        if (args.method === "notify_cancel_by_type") {
            return this._mockMailThreadNotifyCancelByType(
                args.model,
                args.kwargs.notification_type
            );
        }
        return this._super(route, args);
    },
    /**
     * Simulates `_message_compute_author` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @param {Object} [context={}]
     * @returns {Array}
     */
    _MockMailThread_MessageComputeAuthor(model, ids, author_id, email_from, context = {}) {
        if (author_id === undefined) {
            // For simplicity partner is not guessed from email_from here, but
            // that would be the first step on the server.
            let user_id;
            if ("mockedUserId" in context) {
                // can be falsy to simulate not being logged in
                user_id = context.mockedUserId ? context.mockedUserId : this.publicUserId;
            } else {
                user_id = this.currentUserId;
            }
            const user = this.getRecords("res.users", [["id", "=", user_id]], {
                active_test: false,
            })[0];
            const author = this.getRecords("res.partner", [["id", "=", user.partner_id]], {
                active_test: false,
            })[0];
            author_id = author.id;
            email_from = `${author.display_name} <${author.email}>`;
        }

        if (email_from === undefined) {
            if (author_id) {
                const author = this.getRecords("res.partner", [["id", "=", author_id]], {
                    active_test: false,
                })[0];
                email_from = `${author.display_name} <${author.email}>`;
            }
        }

        if (!email_from) {
            throw Error("Unable to log message due to missing author email.");
        }

        return [author_id, email_from];
    },
    /**
     * @param {string} model
     * @param {integer[]} ids
     *
     * @returns {Map<integer:string>}
     * Simulate `_message_compute_subject` on `mail.thread`
     */
    mockMailThread_MessageComputeSubject(model, ids) {
        const records = this.getRecords(model, [["id", "in", ids]]);
        return new Map(records.map((record) => [record.id, record.name || ""]));
    },
    /**
     * Simulates `_message_add_suggested_recipient` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @param {Object} result
     * @param {Object} [param3={}]
     * @param {string} [param3.email]
     * @param {integer} [param3.partner]
     * @param {string} [param3.reason]
     * @returns {Object}
     */
    _mockMailThread_MessageAddSuggestedRecipient(
        model,
        ids,
        result,
        { email, partner, reason = "" } = {}
    ) {
        const record = this.getRecords(model, [["id", "in", "ids"]])[0];
        // for simplicity
        result[record.id].push([partner, email, reason]);
        return result;
    },
    /**
     * Simulates `_message_get_suggested_recipients` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailThread_MessageGetSuggestedRecipients(model, ids) {
        if (model === "res.fake") {
            return this._mockResFake_MessageGetSuggestedRecipients(model, ids);
        }
        const result = ids.reduce((result, id) => (result[id] = []), {});
        const records = this.getRecords(model, [["id", "in", ids]]);
        for (const record in records) {
            if (record.user_id) {
                const user = this.getRecords("res.users", [["id", "=", record.user_id]]);
                if (user.partner_id) {
                    const reason = this.models[model].fields["user_id"].string;
                    this._mockMailThread_MessageAddSuggestedRecipient(
                        result,
                        user.partner_id,
                        reason
                    );
                }
            }
        }
        return result;
    },
    /**
     * Simulates `message_post` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @param {Object} kwargs
     * @param {Object} [context]
     * @returns {Object}
     */
    _mockMailThreadMessagePost(model, ids, kwargs, context) {
        const id = ids[0]; // ensure_one
        if (context?.["mail_post_autofollow"] && kwargs["partner_ids"].length > 0) {
            this._mockMailThreadMessageSubscribe(model, ids, kwargs["partner_ids"]);
        }
        if (kwargs.attachment_ids) {
            const attachments = this.getRecords("ir.attachment", [
                ["id", "in", kwargs.attachment_ids],
                ["res_model", "=", "mail.compose.message"],
                ["res_id", "=", 0],
            ]);
            const attachmentIds = attachments.map((attachment) => attachment.id);
            this.pyEnv["ir.attachment"].write(attachmentIds, {
                res_id: id,
                res_model: model,
            });
            kwargs.attachment_ids = attachmentIds.map((attachmentId) => [4, attachmentId]);
        }
        const subtype_xmlid = kwargs.subtype_xmlid || "mail.mt_note";
        const [author_id, email_from] = this._MockMailThread_MessageComputeAuthor(
            model,
            ids,
            kwargs.author_id,
            kwargs.email_from,
            context
        );
        const values = Object.assign({}, kwargs, {
            author_id,
            email_from,
            is_discussion: subtype_xmlid === "mail.mt_comment",
            is_note: subtype_xmlid === "mail.mt_note",
            model,
            res_id: id,
        });
        delete values.subtype_xmlid;
        const messageId = this.pyEnv["mail.message"].create(values);
        this._mockMailThread_NotifyThread(model, ids, messageId, context?.temporary_id);
        return Object.assign(this._mockMailMessageMessageFormat([messageId])[0], {
            temporary_id: context?.temporary_id,
        });
    },
    /**
     * Simulates `message_subscribe` on `mail.thread`.
     *
     * @private
     * @param {string} model not in server method but necessary for thread mock
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     * @param {integer[]} [subtype_ids]
     * @returns {boolean}
     */
    _mockMailThreadMessageSubscribe(model, ids, partner_ids, subtype_ids) {
        for (const id of ids) {
            for (const partner_id of partner_ids) {
                let followerId = this.pyEnv["mail.followers"].search([
                    ["partner_id", "=", partner_id],
                ])[0];
                if (!followerId) {
                    if (!subtype_ids || subtype_ids.length === 0) {
                        subtype_ids = this.pyEnv["mail.message.subtype"].search([
                            ["default", "=", true],
                            "|",
                            ["res_model", "=", model],
                            ["res_model", "=", false],
                        ]);
                    }
                    followerId = this.pyEnv["mail.followers"].create({
                        is_active: true,
                        partner_id,
                        res_id: id,
                        res_model: model,
                        subtype_ids: subtype_ids,
                    });
                }
                this.pyEnv[model].write(ids, {
                    message_follower_ids: [followerId],
                });
                this.pyEnv["res.partner"].write([partner_id], {
                    message_follower_ids: [followerId],
                });
            }
        }
    },
    /**
     * Simulates `_notify_thread` on `mail.thread`.
     * Simplified version that sends notification to author and channel.
     *
     * @private
     * @param {string} model not in server method but necessary for thread mock
     * @param {integer[]} ids
     * @param {integer} messageId
     * @returns {boolean}
     */
    _mockMailThread_NotifyThread(model, ids, messageId, temporary_id) {
        const message = this.getRecords("mail.message", [["id", "=", messageId]])[0];
        const messageFormat = this._mockMailMessageMessageFormat([messageId])[0];
        const notifications = [];
        if (model === "discuss.channel") {
            // members
            const channels = this.getRecords("discuss.channel", [["id", "=", message.res_id]]);
            for (const channel of channels) {
                // notify update of last_interest_dt
                const now = datetime_to_str(new Date());
                const members = this.getRecords("discuss.channel.member", [
                    ["id", "in", channel.channel_member_ids],
                ]);
                this.pyEnv["discuss.channel.member"].write(
                    members.map((member) => member.id),
                    { last_interest_dt: now }
                );
                for (const member of members) {
                    // simplification, send everything on the current user "test" bus, but it should send to each member instead
                    notifications.push([
                        member,
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
                        message: Object.assign(messageFormat, { temporary_id }),
                    },
                ]);
                if (message.author_id === this.currentPartnerId) {
                    this._mockDiscussChannel_ChannelSeen(ids, message.id);
                }
            }
        }
        const channelMemberOfCurrentUser = this.pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", message.res_id],
            ["partner_id", "=", this.currentPartnerId],
        ]);
        if (channelMemberOfCurrentUser.length === 1) {
            this.pyEnv["bus.bus"]._sendmany(notifications);
        }
    },
    /**
     * Simulates `message_unsubscribe` on `mail.thread`.
     *
     * @private
     * @param {string} model not in server method but necessary for thread mock
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     * @returns {boolean|undefined}
     */
    _mockMailThreadMessageUnsubscribe(model, ids, partner_ids) {
        if (!partner_ids) {
            return true;
        }
        const followers = this.getRecords("mail.followers", [
            ["res_model", "=", model],
            ["res_id", "in", ids],
            ["partner_id", "in", partner_ids || []],
        ]);
        this.pyEnv["mail.followers"].unlink(followers.map((follower) => follower.id));
    },
    /**
     * Simulates `_message_track` on `mail.thread`
     */
    _mockMailThread_MessageTrack(
        modelName,
        trackedFieldNames,
        initialTrackedFieldValuesByRecordId
    ) {
        const trackFieldNamesToField = this.mockFieldsGet(modelName, trackedFieldNames);
        const tracking = {};
        const records = this.models[modelName].records;
        for (const record of records) {
            tracking[record.id] = this._mockMailBaseModel__MailTrack(
                modelName,
                trackFieldNamesToField,
                initialTrackedFieldValuesByRecordId[record.id],
                record
            );
        }
        for (const record of records) {
            const { trackingValueIds, changedFieldNames } = tracking[record.id] || {};
            if (!changedFieldNames || !changedFieldNames.length) {
                continue;
            }
            const changedFieldsInitialValues = {};
            const initialFieldValues = initialTrackedFieldValuesByRecordId[record.id];
            for (const fname in changedFieldNames) {
                changedFieldsInitialValues[fname] = initialFieldValues[fname];
            }
            const subtype = this._mockMailThread_TrackSubtype(changedFieldsInitialValues);
            this._mockMailThreadMessagePost(modelName, [record.id], {
                subtype_id: subtype.id,
                tracking_value_ids: trackingValueIds,
            });
        }
        return tracking;
    },
    /**
     * Simulates `_track_finalize` on `mail.thread`
     */
    _mockMailThread_TrackFinalize(model, initialTrackedFieldValuesByRecordId) {
        this._mockMailThread_MessageTrack(
            model,
            this._mockMailThread_TrackGetFields(model),
            initialTrackedFieldValuesByRecordId
        );
    },
    /**
     * Simulates `_track_get_fields` on `mail.thread`
     */
    _mockMailThread_TrackGetFields(model) {
        return Object.entries(this.models[model].fields).reduce((prev, next) => {
            if (next[1].tracking) {
                prev.push(next[0]);
            }
            return prev;
        }, []);
    },
    /**
     * Simulates `_track_prepare` on `mail.thread`
     */
    _mockMailThread_TrackPrepare(model) {
        const trackedFieldNames = this._mockMailThread_TrackGetFields(model);
        if (!trackedFieldNames.length) {
            return;
        }
        const initialTrackedFieldValuesByRecordId = {};
        for (const record of this.models[model].records) {
            const values = {};
            initialTrackedFieldValuesByRecordId[record.id] = values;
            for (const fname of trackedFieldNames) {
                values[fname] = record[fname];
            }
        }
        return initialTrackedFieldValuesByRecordId;
    },
    /**
     * Simulates `_track_subtype` on `mail.thread`
     */
    _mockMailThread_TrackSubtype(initialFieldValuesByRecordId) {
        return false;
    },
    /**
     * Simulate the `notify_cancel_by_type` on `mail.thread` .
     * Note that this method is overridden by snailmail module but not simulated here.
     */
    _mockMailThreadNotifyCancelByType(model, notificationType) {
        // Query matching notifications
        const notifications = this.getRecords("mail.notification", [
            ["notification_type", "=", notificationType],
            ["notification_status", "in", ["bounce", "exception"]],
        ]).filter((notification) => {
            const message = this.getRecords("mail.message", [
                ["id", "=", notification.mail_message_id],
            ])[0];
            return message.model === model && message.author_id === this.currentPartnerId;
        });
        // Update notification status
        this.pyEnv["mail.notification"].write(
            notifications.map((notification) => notification.id),
            { notification_status: "canceled" }
        );
        // Send bus notifications to update status of notifications in the web client
        this.pyEnv["bus.bus"]._sendone(
            this.pyEnv.currentPartner,
            "mail.message/notification_update",
            {
                elements: this._mockMailMessage_MessageNotificationFormat(
                    notifications.map((notification) => notification.mail_message_id)
                ),
            }
        );
    },
});
