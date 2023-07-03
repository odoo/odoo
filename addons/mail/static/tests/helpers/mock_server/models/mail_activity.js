/* @odoo-module */

import { groupBy, sortBy, unique } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { deserializeDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.model === "mail.activity" && args.method === "action_feedback") {
            const ids = args.args[0];
            return this._mockMailActivityActionFeedback(ids);
        }
        if (args.model === "mail.activity" && args.method === "action_feedback_schedule_next") {
            const ids = args.args[0];
            return this._mockMailActivityActionFeedbackScheduleNext(ids);
        }
        if (args.model === "mail.activity" && args.method === "activity_format") {
            const ids = args.args[0];
            return this._mockMailActivityActivityFormat(ids);
        }
        if (args.model === "mail.activity" && args.method === "get_activity_data") {
            const res_model = args.args[0] || args.kwargs.res_model;
            const domain = args.args[1] || args.kwargs.domain;
            const limit = args[2] || args.kwargs.limit || 0;
            const offset = args[3] || args.kwargs.offset || 0;
            return this._mockMailActivityGetActivityData(res_model, domain, limit, offset);
        }
        if (args.model === "mail.activity" && args.method === "get_activity_data_format") {
            const activity_ids = args.args[0] || args.kwargs.activity_ids;
            const message_ids = args.args[1] || args.kwargs.message_ids;
            return this._mockMailActivityGetActivityDataFormat(activity_ids, message_ids);
        }
        return super._performRPC(route, args);
    },
    /**
     * Simulates `activity_format` on `mail.activity`.
     *
     * @private
     * @param {number[]} ids
     * @returns {Object[]}
     */
    _mockMailActivityActivityFormat(ids) {
        let res = this.mockRead("mail.activity", [ids]);
        res = res.map((record) => {
            if (record.mail_template_ids) {
                record.mail_template_ids = record.mail_template_ids.map((template_id) => {
                    const template = this.getRecords("mail.template", [
                        ["id", "=", template_id],
                    ])[0];
                    return {
                        id: template.id,
                        name: template.name,
                    };
                });
            }
            const [activityType] = record.activity_type_id
                ? this.pyEnv["mail.activity.type"].searchRead([
                      ["id", "=", record.activity_type_id[0]],
                  ])
                : [false];
            if (activityType) {
                record.display_name = activityType.name;
                record.icon = activityType.icon;
            }
            if (record.summary) {
                record.display_name = record.summary;
            }
            return record;
        });
        return res;
    },
    /**
     * Simulates `_action_done` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionDone(ids) {
        const activities = this.getRecords("mail.activity", [["id", "in", ids]]);
        this.mockUnlink("mail.activity", [activities.map((activity) => activity.id)]);
    },
    /**
     * Simulates `action_feedback` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionFeedback(ids) {
        this._mockMailActivityActionDone(ids);
    },
    /**
     * Simulates `action_feedback_schedule_next` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionFeedbackScheduleNext(ids) {
        this._mockMailActivityActionDone(ids);
        return {
            name: "Schedule an Activity",
            view_mode: "form",
            res_model: "mail.activity",
            views: [[false, "form"]],
            type: "ir.actions.act_window",
        };
    },
    /**
     * Simulate partially (time zone not supported) `_compute_state_from_date` on `mail.activity`.
     *
     * @param {DateTime} date_deadline to convert into state
     * @returns {string} dateline status (today, planned or overdue)
     * @private
     */
    _mockComputeStateFromDate(date_deadline) {
        const now = DateTime.now();
        if (date_deadline.hasSame(now, "day")) {
            return "today";
        } else if (date_deadline > now) {
            return "planned";
        }
        return "overdue";
    },
    /**
     * Simulates `get_activity_data` on `mail.activity`.
     *
     * @private
     * @param {string} res_model
     * @param {string} domain
     * @param {number} limit
     * @param {number} offset
     * @returns {Object}
     */
    _mockMailActivityGetActivityData(res_model, domain, limit = 0, offset = 0) {
        const self = this;
        const activityTypes = this.getRecords("mail.activity.type",
            ['|', ['res_model', '=', res_model], ['res_model', '=', false]]
        );
        const displayDoneActivityTypeIds = activityTypes.filter((a)=> a.display_done).map((a) => a.id);
        const allRecords = this.getRecords(res_model, domain ?? []);
        const records = limit ? allRecords.slice(offset, offset + limit) : allRecords;
        const activityDomain = [['res_model', '=', res_model]];
        const domainResIds = domain ? records.map((r) => r.id) : false;
        if (domain) {
            activityDomain.push(['res_id', 'in', domainResIds]);
        }
        const allOngoingActivities = this.getRecords("mail.activity", activityDomain);
        const groupedOngoingActivities = groupBy(allOngoingActivities, a => [a.res_id, a.activity_type_id]);

        const allCompletedActivities = [];
        if (displayDoneActivityTypeIds.length) {
            const mailDomain = [['mail_activity_type_id', 'in', displayDoneActivityTypeIds],
                ['model', '=', res_model]];
            if (domain) {
                mailDomain.push(['res_id', 'in', domainResIds]);
            }
            const mailMessages = this.getRecords("mail.message", mailDomain);
            allCompletedActivities.push(...(mailMessages.map((m) => ({
                activity_type_id: m.mail_activity_type_id,
                attachment_ids: m.attachment_ids,
                date_done: m.date,
                id: m.id,
                res_id: m.res_id,
            }))));
        }
        const allAttachmentIds = allCompletedActivities.map((a) => a.attachment_ids).flat();
        const attachmentsById = allAttachmentIds.length ? Object.fromEntries(
            this.getRecords("ir.attachment", [['id', 'in', allAttachmentIds]]).map((a) => [a.id, a])) : {};
        const groupedCompletedActivities = groupBy(allCompletedActivities, a => [a.res_id, a.activity_type_id]);

        const resIdToDeadline = {};
        const resIdToDateDone = {};
        const groupedActivities = {};
        for (const resIdActivityTypeIdStr of new Set([
            ...Object.keys(groupedCompletedActivities), ...Object.keys(groupedOngoingActivities)])) {
            const [resId, activityTypeId] = resIdActivityTypeIdStr.split(',').map((n) => Number(n));
            const ongoingActivities = groupedOngoingActivities[resIdActivityTypeIdStr] || [];
            const completedActivities = groupedCompletedActivities[resIdActivityTypeIdStr] || [];
            const dateDone = completedActivities.length ?
                DateTime.max(...completedActivities.map(a => deserializeDate(a.date_done))) : false;
            const dateDeadline = ongoingActivities.length ?
                DateTime.min(...ongoingActivities.map(a => deserializeDate(a.date_deadline))) : false;
            if (dateDeadline && ((resIdToDeadline[resId] === undefined) || (dateDeadline < resIdToDeadline[resId]))) {
                resIdToDeadline[resId] = dateDeadline;
            }
            if (dateDone && ((resIdToDateDone[resId] === undefined) || (dateDone > resIdToDateDone[resId]))) {
                resIdToDateDone[resId] = dateDone;
            }
            const isAllActivitiesDone = ongoingActivities.length === 0;
            const distinctAssignees = unique(sortBy(ongoingActivities
                .filter(a => a.user_id), a => a.date_deadline)
                .map(a => a.user_id));
            const closestDate = isAllActivitiesDone ? dateDone : dateDeadline;
            const activityAttachments = completedActivities.map((activity)=>activity.attachment_ids).flat().map(
                (attachmentId) => attachmentsById[attachmentId]);
            const attachmentsInfo = {};
            if (activityAttachments.length) {
                const lastAttachmentCreateDate =
                    DateTime.max(...activityAttachments.map((a) => deserializeDate(a.create_date)));
                const lastAttachment = activityAttachments.find(
                    (a) => lastAttachmentCreateDate.equals(deserializeDate(a.create_date)));
                attachmentsInfo.attachments = {
                    last: {
                        create_date: lastAttachmentCreateDate,
                        id: lastAttachment.id,
                        name: lastAttachment.name,
                    },
                    count: activityAttachments.length,
                };
            }
            if (!(resId in groupedActivities)) {
                groupedActivities[resId] = {};
            }
            groupedActivities[resId][activityTypeId] = {
                completed_activity_ids: completedActivities.map((a) => a.id),
                count_by_state: {
                    ...Object.fromEntries(Object
                        .entries(groupBy(ongoingActivities, a => self._mockComputeStateFromDate(deserializeDate(a.date_deadline))))
                        .map(([state, activities]) => [state, activities.length])
                    ),
                    ...(completedActivities.length ? { done: completedActivities.length } : {}),
                },
                ids: ongoingActivities.map(a => a.id),
                o_closest_date: closestDate ? closestDate.toFormat("yyyy-LL-dd") : false,
                state: isAllActivitiesDone ? 'done' : self._mockComputeStateFromDate(dateDeadline),
                user_ids_ordered_by_deadline: distinctAssignees,
                ...attachmentsInfo,
            };
        }

        return {
            activity_types: activityTypes.map((type) => {
                let mailTemplates = [];
                if (type.mail_template_ids) {
                    mailTemplates = type.mail_template_ids.map((template_id) => {
                        const template = this.getRecords("mail.template", [
                            ["id", "=", template_id],
                        ])[0];
                        return {
                            id: template.id,
                            name: template.name,
                        };
                    });
                }
                return [type.id, type.display_name, mailTemplates, type.display_done];
            }),
            activity_res_ids: sortBy(Object.keys(resIdToDeadline), item => resIdToDeadline[item]).concat(
                sortBy(
                    Object.keys(resIdToDateDone).filter(resId => !(resId in resIdToDeadline)),
                    item => resIdToDateDone[item]
                )
            ).map(idStr => Number(idStr)),
            grouped_activities: groupedActivities,
        };
    },
    /**
     * Simulates `get_activity_data_format` on `mail.activity`.
     *
     * @param {Array} activity_ids
     * @param {Array} message_ids
     * @private
     */
    _mockMailActivityGetActivityDataFormat(activity_ids, message_ids) {
        const completedActivities = this._mockMailMessage_completedActivityFormat(message_ids);
        return {
            activities: this._mockMailActivityActivityFormat(activity_ids),
            attachments: this._mockIrAttachment_attachmentFormat(
                completedActivities.map((activity) => activity.attachment_ids).flat()),
            completed_activities: completedActivities
        };
    },
});
