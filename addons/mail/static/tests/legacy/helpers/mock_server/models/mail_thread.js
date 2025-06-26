/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/mail_thread default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

import { parseEmail } from "@mail/utils/common/format";
import { serializeDateTime, today } from "@web/core/l10n/dates";

patch(MockServer.prototype, {
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
        if (args.method === "message_get_followers") {
            return {};
        }
        if (args.method === "message_post") {
            const id = args.args[0];
            const kwargs = args.kwargs;
            const context = kwargs.context;
            delete kwargs.context;
            return this._mockMailThreadMessagePost(args.model, [id], kwargs, context);
        }
        return super._performRPC(route, args);
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
            const author = this.getRecords(
                "res.partner",
                [["id", "=", this.pyEnv.currentUser.partner_id]],
                {
                    active_test: false,
                }
            )[0];
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
     * Simulates `_get_customer_information` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailThread_GetCustomerInformation(model, ids) {
        return {};
    },
    /**
     * Simulates `_message_add_suggested_recipient` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer} id
     * @param {Object} result
     * @param {Object} [param3={}]
     * @param {string} [param3.email]
     * @param {integer} [param3.partner]
     * @param {string} [param3.reason]
     * @returns {Object}
     */
    _mockMailThread_MessageAddSuggestedRecipient(
        model,
        id,
        result,
        { email, name, partner, lang, reason = "" } = {}
    ) {
        if (email !== undefined && partner === undefined) {
            const partnerInfo = parseEmail(email);
            partner = this.getRecords("res.partner", [["email", "=", partnerInfo[1]]])[0];
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
            const partnerCreateValues = this._mockMailThread_GetCustomerInformation(model, id);
            result.push({
                email,
                name,
                lang,
                reason,
                create_values: partnerCreateValues,
            });
        }

        return result;
    },
    /**
     * Simulates `_message_get_suggested_recipients` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer} id
     * @returns {Object}
     */
    _mockMailThread_MessageGetSuggestedRecipients(model, id) {
        if (model === "res.fake") {
            return this._mockResFake_MessageGetSuggestedRecipients(model, id);
        }
        const result = [];
        const record = this.getRecords(model, [["id", "=", id]])[0];
        if (record.user_id) {
            const user = this.getRecords("res.users", [["id", "=", record.user_id]]);
            if (user.partner_id) {
                const reason = this.models[model].fields["user_id"].string;
                const partner = this.getRecords("res.partner", [["id", "=", user.partner_id]]);
                this._mockMailThread_MessageAddSuggestedRecipient(model, id, result, {
                    email: partner.email,
                    partner,
                    reason,
                });
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
        if (kwargs.partner_emails) {
            kwargs.partner_ids = kwargs.partner_ids || [];
            for (const email of kwargs.partner_emails) {
                const partner = this.getRecords("res.partner", [["email", "=", email]]);
                if (partner.length !== 0) {
                    kwargs.partner_ids.push(partner[0].id);
                } else {
                    const partner_id = this.pyEnv["res.partner"].create(
                        Object.assign({ email }, kwargs.partner_additional_values[email] || {})
                    );
                    kwargs.partner_ids.push(partner_id);
                }
            }
        }
        delete kwargs.partner_emails;
        delete kwargs.partner_additional_values;
        if (context?.["mail_post_autofollow"] && kwargs["partner_ids"]?.length > 0) {
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
        let author_id;
        let email_from;
        const author_guest_id = this.pyEnv.currentUser?._is_public()
            ? this._mockMailGuest__getGuestFromContext()?.id
            : undefined;
        if (!author_guest_id) {
            [author_id, email_from] = this._MockMailThread_MessageComputeAuthor(
                model,
                ids,
                kwargs.author_id,
                kwargs.email_from,
                context
            );
        }

        const values = Object.assign({}, kwargs, {
            author_id,
            author_guest_id,
            email_from,
            is_discussion: subtype_xmlid === "mail.mt_comment",
            is_note: subtype_xmlid === "mail.mt_note",
            model,
            res_id: id,
        });
        delete values.subtype_xmlid;
        const messageId = this.pyEnv["mail.message"].create(values);
        for (const partnerId of kwargs.partner_ids || []) {
            this.pyEnv["mail.notification"].create({
                mail_message_id: messageId,
                notification_type: "inbox",
                res_partner_id: partnerId,
            });
        }
        this._mockMailThread_NotifyThread(model, ids, messageId, context?.temporary_id);
        return { "mail.message": this._mockMailMessageMessageFormat([messageId]) };
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
                    message_follower_ids: [[4, followerId]],
                });
                this.pyEnv["res.partner"].write([partner_id], {
                    message_follower_ids: [[4, followerId]],
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
            const channels = this.getRecords("discuss.channel", [["id", "=", message.res_id]]);
            for (const channel of channels) {
                const now = serializeDateTime(today());
                notifications.push([
                    [channel, "members"],
                    "mail.record/insert",
                    { "discuss.channel": [{ id: channel.id, is_pinned: true }] },
                ]);
                notifications.push([
                    channel,
                    "mail.record/insert",
                    { "discuss.channel": [{ id: channel.id, last_interest_dt: now }] },
                ]);
                notifications.push([
                    channel,
                    "discuss.channel/new_message",
                    { data: { "mail.message": messageFormat }, id: channel.id, temporary_id },
                ]);
            }
        }
        this.pyEnv["bus.bus"]._sendmany(notifications);
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
});
