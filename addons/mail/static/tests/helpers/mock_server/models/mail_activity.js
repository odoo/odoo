/* @odoo-module */

import { groupBy, sortBy, unique } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/models/mail_activity", {
    async _performRPC(route, args) {
        if (args.model === "mail.activity" &&
            ["action_feedback", "action_feedback_and_link_attachment"].includes(args.method)) {
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
            return this._mockMailActivityGetActivityData(res_model, domain);
        }
        return this._super(route, args);
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
     * Simulate partially (time zone not supported) `_compute_state_from_dates` on `mail.activity`.
     *
     * @param {string} dateDone (format YYYY-MM-DD)
     * @param {string} dateDeadline (format YYYY-MM-DD)
     * @returns {string} state
     * @private
     */
    _mockComputeStateFromDates(dateDone, dateDeadline) {
        if (dateDone) {
            return 'done';
        }
        if (dateDeadline === moment().format("YYYY-MM-DD")) {
            return "today";
        } else if (moment(dateDeadline) > moment()) {
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
     * @returns {Object}
     */
    _mockMailActivityGetActivityData(res_model, domain) {
        function infinityToFalse(value) {
            if ( (value === -Infinity) || (value === Infinity) ) {
                return false;
            }
            return value;
        }
        const self = this;
        const records = this.getRecords(res_model, domain);
        const activityIds = records.map((x) => x.activity_ids).flat();
        const activityTypes = this.getRecords("mail.activity.type", []);

        const allActivities = this.getRecords("mail.activity", [["id", "in", activityIds]]);
        const groupedActivities = groupBy(allActivities, a => [a.res_id, a.activity_type_id]);
        // TODO: attachments for upload activity
        const resIdToDeadline = {};
        const resIdToDateDone = {};
        const activityData = {};
        Object.values(groupedActivities).forEach(function (activities) {
            const resId = activities[0].res_id;
            const activityTypeId = activities[0].activity_type_id;
            const activitiesDone = activities.filter(a => a.date_done);
            const activitiesNotDone = activities.filter(a => !a.date_done);
            const isAllActivitiesDone = activitiesNotDone.length === 0;
            const dateDoneUnix = infinityToFalse(Math.max(...activitiesDone.map(a => moment(a.date_done).unix())));
            const dateDeadlineUnix = infinityToFalse(Math.min(...activitiesNotDone.map(a => moment(a.date_deadline).unix())));
            if (dateDeadlineUnix && ((resIdToDeadline[resId] === undefined) || (dateDeadlineUnix < resIdToDeadline[resId]))) {
                resIdToDeadline[resId] = dateDeadlineUnix;
            }
            if (dateDoneUnix && ((resIdToDateDone[resId] === undefined) || (dateDoneUnix > resIdToDateDone[resId]))) {
                resIdToDateDone[resId] = dateDoneUnix;
            }
            const distinctAssignees = unique(sortBy(activitiesDone
                .filter(a => a.user_id), a => a.date_deadline)
                .map(a => a.user_id));
            const closestDateUnix = isAllActivitiesDone ? dateDoneUnix : dateDeadlineUnix;
            const data = {
                user_ids_ordered_by_deadline: distinctAssignees,
                count: activities.length,
                ids: activities.map(a => a.id),
                o_closest_date: closestDateUnix ? moment.unix(closestDateUnix).format("YYYY-MM-DD") : false,
                state: self._mockComputeStateFromDates(isAllActivitiesDone, moment.unix(dateDeadlineUnix).format("YYYY-MM-DD")),
            };
            // TODO: add attachments
            if (!(resId in activityData)) {
                activityData[resId] = {};
            }
            activityData[resId][activityTypeId] = data
        });

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
                return [type.id, type.display_name, mailTemplates];
            }),
            activity_res_ids: sortBy(Object.keys(resIdToDeadline), item => resIdToDeadline[item]).concat(
                sortBy(
                    Object.keys(resIdToDateDone).filter(resId => !(resId in resIdToDeadline)),
                    item => resIdToDateDone[item]
                )
            ).map(idStr => Number(idStr)),
            grouped_activities: activityData,
        };
    },
});
