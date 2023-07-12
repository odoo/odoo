/* @odoo-module */

import { sortBy } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { serializeDate } from "@web/core/l10n/dates";

const { DateTime} = luxon;

patch(MockServer.prototype, "mail/models/mail_activity", {
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
     * Simulates `get_activity_data` on `mail.activity`.
     *
     * @private
     * @param {string} res_model
     * @param {string} domain
     * @returns {Object}
     */
    _mockMailActivityGetActivityData(res_model, domain) {
        const self = this;
        const records = this.getRecords(res_model, domain);

        const activityTypes = this.getRecords("mail.activity.type", []);
        const activityIds = records.map((x) => x.activity_ids).flat();

        const groupedActivities = {};
        const resIdToDeadline = {};
        const groups = self.mockReadGroup("mail.activity", {
            domain: [["id", "in", activityIds]],
            fields: [
                "res_id",
                "activity_type_id",
                "ids:array_agg(id)",
                "date_deadline:min(date_deadline)",
            ],
            groupby: ["res_id", "activity_type_id"],
            lazy: false,
        });
        groups.forEach(function (group) {
            // mockReadGroup doesn't correctly return all asked fields
            const activites = self.getRecords("mail.activity", group.__domain);
            group.activity_type_id = group.activity_type_id[0];
            let minDate;
            activites.forEach(function (activity) {
                if (!minDate || moment(activity.date_deadline) < moment(minDate)) {
                    minDate = activity.date_deadline;
                }
            });
            group.date_deadline = minDate;
            resIdToDeadline[group.res_id] = minDate;
            let state;
            if (group.date_deadline === serializeDate(DateTime.now())) {
                state = "today";
            } else if (moment(group.date_deadline) > moment()) {
                state = "planned";
            } else {
                state = "overdue";
            }
            if (!groupedActivities[group.res_id]) {
                groupedActivities[group.res_id] = {};
            }
            groupedActivities[group.res_id][group.activity_type_id] = {
                count: group.__count,
                state: state,
                o_closest_deadline: group.date_deadline,
                ids: activites.map((x) => x.id),
            };
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
            activity_res_ids: sortBy(
                records.map((x) => x.id),
                (id) => moment(resIdToDeadline[id])
            ),
            grouped_activities: groupedActivities,
        };
    },
});
