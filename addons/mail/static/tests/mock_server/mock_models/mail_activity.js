/** @odoo-module */

import { Domain } from "@web/core/domain";
import { groupBy, sortBy, unique } from "@web/core/utils/arrays";
import { deserializeDate, serializeDate, today } from "@web/core/l10n/dates";
import { fields, models } from "@web/../tests/web_test_helpers";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

const { DateTime } = luxon;

export class MailActivity extends models.ServerModel {
    _name = "mail.activity";

    chaining_type = fields.Generic({ default: "suggest" });

    /**
     * Simulates `action_feedback` on `mail.activity`.
     *
     * @param {number[]} ids
     */
    action_feedback(ids) {
        const activities = this._filter([["id", "in", ids]]);
        const activityTypes = this.env["mail.activity.type"]._filter([
            ["id", "in", unique(activities.map((a) => a.activity_type_id))],
        ]);
        const activityTypeById = Object.fromEntries(
            activityTypes.map((actType) => [actType.id, actType])
        );
        this.write(
            activities
                .filter((act) => activityTypeById[act.activity_type_id].keep_done)
                .map((act) => act.id),
            { active: false, date_done: serializeDate(today()), state: "done" }
        );
        this.unlink(
            activities
                .filter((act) => !activityTypeById[act.activity_type_id].keep_done)
                .map((act) => act.id)
        );
    }

    /**
     * Simulates `action_feedback_schedule_next` on `mail.activity`.
     *
     * @param {number[]} ids
     */
    action_feedback_schedule_next(ids) {
        this._actionDone(ids);
        return {
            name: "Schedule an Activity",
            view_mode: "form",
            res_model: "mail.activity",
            views: [[false, "form"]],
            type: "ir.actions.act_window",
        };
    }

    /**
     * Simulates `activity_format` on `mail.activity`.
     *
     * @param {number[]} ids
     */
    activity_format(ids) {
        return this.read(ids).map((record) => {
            if (record.mail_template_ids) {
                record.mail_template_ids = record.mail_template_ids.map((template_id) => {
                    const template = this.env["mail.template"]._filter([
                        ["id", "=", template_id],
                    ])[0];
                    return {
                        id: template.id,
                        name: template.name,
                    };
                });
            }
            const [activityType] = record.activity_type_id
                ? this.env["mail.activity.type"].search_read([
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
    }

    /**
     * Simulates `get_activity_data` on `mail.activity`.
     *
     * @param {string} resModel
     * @param {string} domain
     * @param {number} limit
     * @param {number} offset
     * @param {boolean} fetchDone
     * @param {KwArgs<>} [kwargs]
     */
    get_activity_data(resModel, domain, limit, offset, fetchDone, kwargs = {}) {
        resModel = kwargs.res_model || resModel;
        domain = kwargs.domain || domain;
        limit = kwargs.limit || limit || 0;
        offset = kwargs.offset || offset || 0;
        fetchDone = kwargs.fetch_done ?? fetchDone ?? false;

        // 1. Retrieve all ongoing and completed activities according to the parameters
        const activityTypes = this.env["mail.activity.type"]._filter([
            "|",
            ["res_model", "=", resModel],
            ["res_model", "=", false],
        ]);
        // Remove domain term used to filter record having "done" activities (not understood by the _filter mock)
        domain = Domain.removeDomainLeaves(new Domain(domain ?? []).toList(), [
            "activity_ids.active",
        ]).toList();
        const allRecords = this.env[resModel]._filter(domain ?? []);
        const records = limit ? allRecords.slice(offset, offset + limit) : allRecords;
        const activityDomain = [["res_model", "=", resModel]];
        const isFiltered = domain || limit || offset;
        const domainResIds = records.map((r) => r.id);
        if (isFiltered) {
            activityDomain.push(["res_id", "in", domainResIds]);
        }
        const allActivities = this._filter(activityDomain, { active_test: !resModel });
        const allOngoing = allActivities.filter((a) => a.active);
        const allCompleted = allActivities.filter((a) => !a.active);

        // 2. Get attachment of completed activities
        let attachmentsById;
        if (allCompleted.length) {
            const attachmentIds = allCompleted.map((a) => a.attachment_ids).flat();
            attachmentsById = attachmentIds.length
                ? Object.fromEntries(
                      this.env["ir.attachment"]
                          ._filter([["id", "in", attachmentIds]])
                          .map((a) => [a.id, a])
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
                                this._computeStateFromDate(deserializeDate(a.date_deadline))
                            )
                        ).map(([state, activities]) => [state, activities.length])
                    ),
                    ...(completed.length ? { done: completed.length } : {}),
                },
                ids: ongoing.map((a) => a.id).concat(completed.map((a) => a.id)),
                reporting_date: reportingDate ? reportingDate.toFormat("yyyy-LL-dd") : false,
                state: ongoing.length ? this._computeStateFromDate(dateDeadline) : "done",
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
                const templates = (type.mail_template_ids || []).map((template_id) => {
                    const { id, name } = this.env["mail.template"]._filter([
                        ["id", "=", template_id],
                    ])[0];
                    return { id, name };
                });
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
    }

    /**
     * Simulates `_action_done` on `mail.activity`.
     *
     * @param {number[]} ids
     */
    _actionDone(ids) {
        this.action_feedback(ids);
    }

    /**
     * Simulate partially (time zone not supported) `_compute_state_from_date` on `mail.activity`.
     *
     * @param {DateTime} date_deadline to convert into state
     * @returns {"today" | "planned" | "overdue"}
     */
    _computeStateFromDate(date_deadline) {
        const now = DateTime.now();
        if (date_deadline.hasSame(now, "day")) {
            return "today";
        } else if (date_deadline > now) {
            return "planned";
        }
        return "overdue";
    }
}
