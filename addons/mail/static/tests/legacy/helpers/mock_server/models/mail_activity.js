/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/mail_activity default=false */

import { Domain } from "@web/core/domain";
import { groupBy, sortBy, unique } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { deserializeDate, serializeDate, today } from "@web/core/l10n/dates";

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
            return { "mail.activity": this._mockMailActivityActivityFormat(ids) };
        }
        if (args.model === "mail.activity" && args.method === "get_activity_data") {
            const res_model = args.args[0] || args.kwargs.res_model;
            const domain = args.args[1] || args.kwargs.domain;
            const limit = args[2] || args.kwargs.limit || 0;
            const offset = args[3] || args.kwargs.offset || 0;
            const fetch_done = args[4] || args.kwargs.fetch_done || false;
            return this._mockMailActivityGetActivityData(
                res_model,
                domain,
                limit,
                offset,
                fetch_done
            );
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
                ? this.pyEnv["mail.activity.type"].search_read([
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
            const user = this.pyEnv["res.users"].search_read([["id", "=", record.user_id[0]]])[0];
            record.persona = this._mockResPartnerMailPartnerFormat([user.partner_id[0]]).get(
                user.partner_id[0]
            );
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
        this._mockMailActivityActionFeedback(ids);
    },
    /**
     * Simulates `action_feedback` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionFeedback(ids, attachment_ids = null) {
        const activities = this.getRecords("mail.activity", [["id", "in", ids]]);
        const activityTypes = this.getRecords("mail.activity.type", [
            ["id", "in", unique(activities.map((a) => a.activity_type_id))],
        ]);
        const activityTypeById = Object.fromEntries(
            activityTypes.map((actType) => [actType.id, actType])
        );
        this.mockWrite("mail.activity", [
            activities
                .filter((act) => activityTypeById[act.activity_type_id].keep_done)
                .map((act) => act.id),
            { active: false, date_done: serializeDate(today()), state: "done" },
        ]);
        this.mockUnlink("mail.activity", [
            activities
                .filter((act) => !activityTypeById[act.activity_type_id].keep_done)
                .map((act) => act.id),
        ]);
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
     * Simulates `get_activity_data` on `mail.activity`.
     *
     * @private
     * @param {string} res_model
     * @param {string} domain
     * @param {number} limit
     * @param {number} offset
     * @returns {Object}
     */
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
     * @param {boolean} fetch_done
     * @returns {Object}
     */
    _mockMailActivityGetActivityData(res_model, domain, limit = 0, offset = 0, fetch_done = false) {
        const self = this;

        // 1. Retrieve all ongoing and completed activities according to the parameters
        const activityTypes = this.getRecords("mail.activity.type", [
            "|",
            ["res_model", "=", res_model],
            ["res_model", "=", false],
        ]);
        // Remove domain term used to filter record having "done" activities (not understood by the getRecords mock)
        domain = Domain.removeDomainLeaves(new Domain(domain ?? []).toList(), [
            "activity_ids.active",
        ]).toList();
        const allRecords = this.getRecords(res_model, domain ?? []);
        const records = limit ? allRecords.slice(offset, offset + limit) : allRecords;
        const activityDomain = [["res_model", "=", res_model]];
        const isFiltered = domain || limit || offset;
        const domainResIds = records.map((r) => r.id);
        if (isFiltered) {
            activityDomain.push(["res_id", "in", domainResIds]);
        }
        const allActivities = this.getRecords("mail.activity", activityDomain, {
            active_test: !fetch_done,
        });
        const allOngoing = allActivities.filter((a) => a.active);
        const allCompleted = allActivities.filter((a) => !a.active);

        // 2. Get attachment of completed activities
        let attachmentsById;
        if (allCompleted.length) {
            const attachmentIds = allCompleted.map((a) => a.attachment_ids).flat();
            attachmentsById = attachmentIds.length
                ? Object.fromEntries(
                      this.getRecords("ir.attachment", [["id", "in", attachmentIds]]).map((a) => [
                          a.id,
                          a,
                      ])
                  )
                : {};
        } else {
            attachmentsById = {};
        }

        // 3. Group activities per records and activity type
        const groupedCompleted = groupBy(allCompleted, (a) => [a.res_id, a.activity_type_id]);
        const groupedOngoing = groupBy(allOngoing, (a) => [a.res_id, a.activity_type_id]);

        // 4. Format data
        const resIdToDeadline = {};
        const resIdToDateDone = {};
        const groupedActivities = {};
        for (const resIdStrTuple of new Set([
            ...Object.keys(groupedCompleted),
            ...Object.keys(groupedOngoing),
        ])) {
            const [resId, activityTypeId] = resIdStrTuple.split(",").map((n) => Number(n));
            const ongoing = groupedOngoing[resIdStrTuple] || [];
            const completed = groupedCompleted[resIdStrTuple] || [];
            const dateDone = completed.length
                ? DateTime.max(...completed.map((a) => deserializeDate(a.date_done)))
                : false;
            const dateDeadline = ongoing.length
                ? DateTime.min(...ongoing.map((a) => deserializeDate(a.date_deadline)))
                : false;
            if (
                dateDeadline &&
                (resIdToDeadline[resId] === undefined || dateDeadline < resIdToDeadline[resId])
            ) {
                resIdToDeadline[resId] = dateDeadline;
            }
            if (
                dateDone &&
                (resIdToDateDone[resId] === undefined || dateDone > resIdToDateDone[resId])
            ) {
                resIdToDateDone[resId] = dateDone;
            }
            const userAssignedIds = unique(
                sortBy(
                    ongoing.filter((a) => a.user_id),
                    (a) => a.date_deadline
                ).map((a) => a.user_id)
            );
            const reportingDate = ongoing.length ? dateDeadline : dateDone;
            const attachments = completed
                .map((act) => act.attachment_ids)
                .flat()
                .map((attachmentId) => attachmentsById[attachmentId]);
            const attachmentsInfo = {};
            if (attachments.length) {
                const lastAttachmentCreateDate = DateTime.max(
                    ...attachments.map((a) => deserializeDate(a.create_date))
                );
                const mostRecentAttachment = attachments.find((a) =>
                    lastAttachmentCreateDate.equals(deserializeDate(a.create_date))
                );
                attachmentsInfo.attachments = {
                    most_recent_id: mostRecentAttachment.id,
                    most_recent_name: mostRecentAttachment.name,
                    count: attachments.length,
                };
            }
            if (!(resId in groupedActivities)) {
                groupedActivities[resId] = {};
            }
            groupedActivities[resId][activityTypeId] = {
                count_by_state: {
                    ...Object.fromEntries(
                        Object.entries(
                            groupBy(ongoing, (a) =>
                                self._mockComputeStateFromDate(deserializeDate(a.date_deadline))
                            )
                        ).map(([state, activities]) => [state, activities.length])
                    ),
                    ...(completed.length ? { done: completed.length } : {}),
                },
                ids: ongoing.map((a) => a.id).concat(completed.map((a) => a.id)),
                reporting_date: reportingDate ? reportingDate.toFormat("yyyy-LL-dd") : false,
                state: ongoing.length ? self._mockComputeStateFromDate(dateDeadline) : "done",
                user_assigned_ids: userAssignedIds,
                ...attachmentsInfo,
            };
        }

        const ongoingResIds = sortBy(Object.keys(resIdToDeadline), (item) => resIdToDeadline[item]);
        const completedResIds = sortBy(
            Object.keys(resIdToDateDone).filter((resId) => !(resId in resIdToDeadline)),
            (item) => resIdToDateDone[item]
        );
        return {
            activity_types: activityTypes.map((type) => {
                let templates = [];
                if (type.mail_template_ids) {
                    templates = type.mail_template_ids.map((template_id) => {
                        const template = this.getRecords("mail.template", [
                            ["id", "=", template_id],
                        ])[0];
                        return {
                            id: template.id,
                            name: template.name,
                        };
                    });
                }
                return {
                    id: type.id,
                    name: type.display_name,
                    template_ids: templates,
                    keep_done: type.keep_done,
                };
            }),
            activity_res_ids: ongoingResIds.concat(completedResIds).map((idStr) => Number(idStr)),
            grouped_activities: groupedActivities,
        };
    },
});
