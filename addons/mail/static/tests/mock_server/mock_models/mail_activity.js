import { Domain } from "@web/core/domain";
import { groupBy, sortBy, unique } from "@web/core/utils/arrays";
import { deserializeDate, serializeDate, today } from "@web/core/l10n/dates";
import { fields, models, serverState } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_SEARCH_ID, DEFAULT_MAIL_VIEW_ID } from "./constants";
import { MailActivityType } from "./mail_activity_type";
import { parseModelParams } from "../mail_mock_server";

const { DateTime } = luxon;

export class MailActivity extends models.ServerModel {
    _name = "mail.activity";
    _views = {
        [`search,${DEFAULT_MAIL_SEARCH_ID}`]: /* xml */ `<search/>`,
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: /* xml */ `<form/>`,
    };

    activity_type_id = fields.Many2one({
        relation: "mail.activity.type",
        default() {
            return MailActivityType._records[0].id;
        },
    });
    user_id = fields.Many2one({ relation: "res.users", default: () => serverState.userId });
    chaining_type = fields.Generic({ default: "suggest" });
    activity_category = fields.Generic({ related: false }); // removes related from server to ease creating activities
    res_model = fields.Char({ string: "Related Document Model", related: false }); // removes related from server to ease creating activities

    /** @param {number[]} ids */
    action_feedback(ids) {
        /** @type {import("mock_models").MailActivityType} */
        const MailActivityType = this.env["mail.activity.type"];

        const activities = this._filter([["id", "in", ids]]);
        const activityTypes = MailActivityType._filter([
            ["id", "in", unique(activities.map((a) => a.activity_type_id))],
        ]);
        const activityTypeById = Object.fromEntries(
            activityTypes._records.map((actType) => [actType.id, actType])
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

    /** @param {number[]} ids */
    action_feedback_schedule_next(ids) {
        this._action_done(ids);
        return {
            name: "Schedule an Activity",
            view_mode: "form",
            res_model: "mail.activity",
            views: [[false, "form"]],
            type: "ir.actions.act_window",
        };
    }

    /** @param {number[]} ids */
    activity_format(ids) {
        /** @type {import("mock_models").MailActivityType} */
        const MailActivityType = this.env["mail.activity.type"];
        /** @type {import("mock_models").MailTemplate} */
        const MailTemplate = this.env["mail.template"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        return this.read(ids).map((record) => {
            const activityType = record.activity_type_id
                ? MailActivityType._records.find((r) => r.id === record.activity_type_id[0])
                : false;
            if (activityType) {
                record.display_name = activityType.name;
                record.icon = activityType.icon;
                record.mail_template_ids = activityType.mail_template_ids.map((template_id) => {
                    const template = MailTemplate._filter([["id", "=", template_id]])[0];
                    return {
                        id: template.id,
                        name: template.name,
                    };
                });
            }
            if (record.summary) {
                record.display_name = record.summary;
            }
            const user = ResUsers.search_read([["id", "=", record.user_id[0]]])[0];
            record.persona = ResPartner.mail_partner_format([user.partner_id[0]])[
                user.partner_id[0]
            ];
            return record;
        });
    }

    /**
     * @param {string} res_model
     * @param {string} domain
     * @param {number} limit
     * @param {number} offset
     * @param {boolean} fetch_done
     */
    get_activity_data(res_model, domain, limit = 0, offset = 0, fetch_done) {
        const kwargs = parseModelParams(
            arguments,
            "res_model",
            "domain",
            "limit",
            "offset",
            "fetch_done"
        );
        res_model = kwargs.res_model;
        domain = kwargs.domain;
        limit = kwargs.limit || 0;
        offset = kwargs.offset || 0;
        fetch_done = kwargs.fetch_done ?? false;

        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").MailActivityType} */
        const MailActivityType = this.env["mail.activity.type"];
        /** @type {import("mock_models").MailTemplate} */
        const MailTemplate = this.env["mail.template"];

        // 1. Retrieve all ongoing and completed activities according to the parameters
        const activityTypes = MailActivityType._filter([
            "|",
            ["res_model", "=", res_model],
            ["res_model", "=", false],
        ]);
        // Remove domain term used to filter record having "done" activities (not understood by the _filter mock)
        domain = Domain.removeDomainLeaves(new Domain(domain ?? []).toList(), [
            "activity_ids.active",
        ]).toList();
        const allRecords = this.env[res_model]._filter(domain ?? []);
        const records = limit ? allRecords.slice(offset, offset + limit) : allRecords;
        const activityDomain = [["res_model", "=", res_model]];
        const isFiltered = domain || limit || offset;
        const domainResIds = records.map((r) => r.id);
        if (isFiltered) {
            activityDomain.push(["res_id", "in", domainResIds]);
        }
        const allActivities = this._filter(activityDomain, { active_test: !res_model });
        const allOngoing = allActivities.filter((a) => a.active);
        const allCompleted = allActivities.filter((a) => !a.active);
        // 2. Get attachment of completed activities
        let attachmentsById;
        if (allCompleted.length) {
            const attachmentIds = allCompleted.map((a) => a.attachment_ids).flat();
            attachmentsById = attachmentIds.length
                ? Object.fromEntries(
                      IrAttachment._filter([["id", "in", attachmentIds]]).map((a) => [a.id, a])
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
                                this._compute_state_from_date(deserializeDate(a.date_deadline))
                            )
                        ).map(([state, activities]) => [state, activities.length])
                    ),
                    ...(completed.length ? { done: completed.length } : {}),
                },
                ids: ongoing.map((a) => a.id).concat(completed.map((a) => a.id)),
                reporting_date: reportingDate ? reportingDate.toFormat("yyyy-LL-dd") : false,
                state: ongoing.length ? this._compute_state_from_date(dateDeadline) : "done",
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
                    const { id, name } = MailTemplate._filter([["id", "=", template_id]])[0];
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

    /** @param {number[]} ids */
    _action_done(ids) {
        this.action_feedback(ids);
    }

    /**
     * @param {DateTime} date_deadline to convert into state
     * @returns {"today" | "planned" | "overdue"}
     */
    _compute_state_from_date(date_deadline) {
        const now = DateTime.now();
        if (date_deadline.hasSame(now, "day")) {
            return "today";
        } else if (date_deadline > now) {
            return "planned";
        }
        return "overdue";
    }
}
