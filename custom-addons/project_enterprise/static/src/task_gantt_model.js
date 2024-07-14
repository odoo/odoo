/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { deserializeDate, deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { GanttModel } from "@web_gantt/gantt_model";
import { sortBy } from "@web/core/utils/arrays";

const MAP_MANY_2_MANY_FIELDS = [
    {
        many2many_field: "personal_stage_type_ids",
        many2one_field: "personal_stage_type_id",
    },
];

export class TaskGanttModel extends GanttModel {
    //-------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    getDialogContext() {
        const context = super.getDialogContext(...arguments);
        this._replaceSpecialMany2manyKeys(context);
        if ("user_ids" in context && !context.user_ids) {
            delete context.user_ids;
        }
        return context;
    }

    /**
     * @override
     */
    reschedule(ids, schedule, callback) {
        if (!schedule.smart_task_scheduling) {
            return super.reschedule(...arguments);
        }
        if (!Array.isArray(ids)) {
            ids = [ids];
        }

        const allData = this._scheduleToData(schedule);
        const endDateTime = deserializeDateTime(allData.date_deadline).endOf(
            this.metaData.scale.id
        );

        const data = this.removeRedundantData(allData, ids);
        delete data.name;
        return this.mutex.exec(async () => {
            try {
                const result = await this.orm.call(
                    this.metaData.resModel,
                    "schedule_tasks",
                    [ids, data],
                    {
                        context: {
                            ...this.searchParams.context,
                            last_date_view: serializeDateTime(endDateTime),
                            cell_part: this.metaData.scale.cellPart,
                        },
                    }
                );
                if (callback) {
                    callback(result);
                }
            } finally {
                this.fetchData();
            }
        });
    }

    async unscheduleTask(id) {
        await this.orm.call(
            'project.task',
            'action_unschedule_task',
            [id],
        );
        this.fetchData();
    }

    //-------------------------------------------------------------------------
    // Protected
    //-------------------------------------------------------------------------

    /**
     * Retrieve the milestone data based on the task domain.
     * @override
     */
    async _fetchData(metaData) {
        const startDate = metaData.startDate.toISODate();
        const scale = metaData.scale.id;
        this.searchParams.context = {
            ...this.searchParams.context,
            gantt_start_date: startDate,
            gantt_scale: scale,
        };
        const proms = [super._fetchData(...arguments)];
        const milestones = [];
        if (!this.orm.isSample && !this.env.isSmall) {
            const prom = this.orm
                .call("project.milestone", "search_milestone_from_task", [], {
                    task_domain: this.searchParams.domain,
                    milestone_domain: [
                        ["deadline", "<=", metaData.stopDate.toISODate()],
                        ["deadline", ">=", startDate],
                    ],
                    fields: [
                        "name",
                        "deadline",
                        "is_deadline_exceeded",
                        "is_reached",
                        "project_id",
                    ],
                    order: "project_id ASC, deadline ASC",
                    context: this.searchParams.context,
                })
                .then((result) => {
                    for (const milestone of result) {
                        milestones.push({
                            ...milestone,
                            deadline: deserializeDate(milestone.deadline),
                        });
                    }
                });
            proms.push(prom);
        }
        await Promise.all(proms);
        this.data.milestones = sortBy(milestones, (m) => m.deadline);
    }

    /**
     * @override
     */
    _generateRows(_, params) {
        const { groupedBy, groups, parentGroup } = params;
        if (groupedBy.length) {
            const groupedByField = groupedBy[0];
            if (groupedByField === "user_ids") {
                // Here we are generating some rows under a common "parent" (if any).
                // We make sure that a row with resId = false for "user_id"
                // ('Unassigned Tasks') and same "parent" will be added by adding
                // a suitable fake group to groups (a subset of the groups returned
                // by read_group).
                const fakeGroup = Object.assign({}, ...parentGroup);
                groups.push(fakeGroup);
            }
        }
        const rows = super._generateRows(...arguments);

        // keep empty row to the head and sort the other rows alphabetically
        // except when grouping by stage or personal stage
        if (!["stage_id", "personal_stage_type_ids"].includes(groupedBy[0])) {
            rows.sort((a, b) => {
                if (a.resId && !b.resId) {
                    return 1;
                } else if (!a.resId && b.resId) {
                    return -1;
                } else {
                    return a.name.localeCompare(b.name);
                }
            });
        }
        return rows;
    }

    /**
     * @override
     */
    _getRowName(_, groupedByField, value) {
        if (!value) {
            if (groupedByField === "user_ids") {
                return _t("👤 Unassigned");
            } else if (groupedByField === "project_id") {
                return _t("🔒 Private");
            }
        }
        return super._getRowName(...arguments);
    }

    /**
     * In the case of special Many2many Fields, like personal_stage_type_ids in project.task
     * model, we don't want to write the many2many field but use the inverse method of the
     * linked Many2one field, in this case the personal_stage_type_id, to create or update the
     * record - here set the stage_id - in the personal_stage_type_ids.
     *
     * This is mandatory since the python ORM doesn't support the creation of
     * a personnal stage from scratch. If this method is not overriden, then an entry
     * will be inserted in the project_task_user_rel.
     * One for the faked Many2many user_ids field (1), and a second one for the other faked
     * Many2many personal_stage_type_ids field (2).
     *
     * While the first one meets the constraint on the project_task_user_rel, the second one
     * fails because it specifies no user_id; It tries to insert (task_id, stage_id) into the
     * relation.
     *
     * If we don't remove those key from the context, the ORM will face two problems :
     * - It will try to insert 2 entries in the project_task_user_rel
     * - It will try to insert an incorrect entry in the project_task_user_rel
     *
     * @param {Object} object
     */
    _replaceSpecialMany2manyKeys(object) {
        for (const { many2many_field, many2one_field } of MAP_MANY_2_MANY_FIELDS) {
            if (many2many_field in object) {
                object[many2one_field] = object[many2many_field][0];
                delete object[many2many_field];
            }
        }
    }

    /**
     * @override
     */
    _scheduleToData() {
        const data = super._scheduleToData(...arguments);
        this._replaceSpecialMany2manyKeys(data);
        return data;
    }
}
