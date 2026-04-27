import { _t } from "@web/core/l10n/translation";
import { deserializeDate, deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { GanttModel } from "@web_gantt/gantt_model";
import { sortBy } from "@web/core/utils/arrays";
import { Domain } from "@web/core/domain";
import { useProjectModelActions } from "../project_highlight_tasks";

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

    setup() {
        super.setup(...arguments);
        this.getHighlightIds = useProjectModelActions({
            getContext: () => this.env.searchModel._context,
            getHighlightPlannedIds: () => this.env.searchModel.highlightPlannedIds,
        }).getHighlightIds;
    }

    getDialogContext() {
        const context = super.getDialogContext(...arguments);
        this._replaceSpecialMany2manyKeys(context);
        if ("user_ids" in context && !context.user_ids) {
            delete context.user_ids;
        }
        return context;
    }

    toggleHighlightPlannedFilter(ids) {
        super.toggleHighlightPlannedFilter(...arguments);
        this.env.searchModel.toggleHighlightPlannedFilter(ids);
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
                if (result && Array.isArray(result) && result.length > 1) {
                    this.toggleHighlightPlannedFilter(Object.keys(result[1]).map(Number));
                }
                if (callback) {
                    callback(result);
                }
            } finally {
                this.fetchData();
            }
        });
    }

    _reschedule(ids, data, context) {
        return this.orm.call(this.metaData.resModel, "web_gantt_write", [ids, data], {
            context,
        });
    }

    async unscheduleTask(id) {
        await this.orm.call("project.task", "action_unschedule_task", [id]);
        this.fetchData();
    }

    //-------------------------------------------------------------------------
    // Protected
    //-------------------------------------------------------------------------

    /**
     * Retrieve the milestone data based on the task domain and the project deadline if applicable.
     * @override
     */
    async _fetchData(metaData, additionalContext) {
        const globalStart = metaData.globalStart.toISODate();
        const globalStop = metaData.globalStop.toISODate();
        const scale = metaData.scale.unit;
        additionalContext = {
            ...(additionalContext || {}),
            gantt_start_date: globalStart,
            gantt_scale: scale,
        };
        const proms = [this.getHighlightIds(), super._fetchData(metaData, additionalContext)];
        let milestones = [];
        const projectDeadlines = [];
        const projectStartDates = [];
        if (!this.orm.isSample && !this.env.isSmall) {
            const prom = this.orm
                .call("project.task", "get_all_deadlines", [globalStart, globalStop], {
                    context: this.searchParams.context,
                })
                .then(({ milestone_id, project_id }) => {
                    milestones = milestone_id.map((m) => ({
                        ...m,
                        deadline: deserializeDate(m.deadline),
                    }));
                    for (const project of project_id) {
                        const dateEnd = project.date;
                        const dateStart = project.date_start;
                        if (dateEnd >= globalStart && dateEnd <= globalStop) {
                            projectDeadlines.push({
                                ...project,
                                date: deserializeDate(dateEnd),
                            });
                        }
                        if (dateStart >= globalStart && dateStart <= globalStop) {
                            projectStartDates.push({
                                ...project,
                                date: deserializeDate(dateStart),
                            });
                        }
                    }
                });
            proms.push(prom);
        }
        this.highlightIds = (await Promise.all(proms))[0];
        this.data.milestones = sortBy(milestones, (m) => m.deadline);
        this.data.projectDeadlines = sortBy(projectDeadlines, (d) => d.date);
        this.data.projectStartDates = sortBy(projectStartDates, (d) => d.date);
    }

    /**
     * @override
     */
    _generateRows(metaData, params) {
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

    /**
     * @override
     */
    load(searchParams) {
        const { context, domain, groupBy } = searchParams;
        let displayUnassigned = false;
        if (groupBy.length === 0 || groupBy[groupBy.length - 1] === "user_ids") {
            for (const node of domain) {
                if (node.length === 3 && node[0] === "user_ids.name" && node[1] === "ilike") {
                    displayUnassigned = true;
                }
            }
        }
        if (displayUnassigned) {
            const domainList = new Domain(domain).toList();
            const projectId = context?.default_project_id || null;
            let unassignedOnlyDomain = new Domain([["user_ids", "=", false]]);
            if (projectId) {
                unassignedOnlyDomain = Domain.and([
                    unassignedOnlyDomain,
                    [["project_id", "=", projectId]],
                ]);
            }
            searchParams.domain = Domain.or([domainList, unassignedOnlyDomain]).toList();
        }
        return super.load({ ...searchParams, context: { ...context }, displayUnassigned });
    }
}
