import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { GanttModel } from "@web_gantt/gantt_model";
import { usePlanningModelActions } from "../planning_hooks";
import { Domain } from "@web/core/domain";
import { pick } from "@web/core/utils/objects";
import { router } from "@web/core/browser/router";
import { getRangeFromDate, localStartOf, localEndOf } from "@web_gantt/gantt_helpers";

const GROUPBY_COMBINATIONS = [
    "role_id",
    "role_id,resource_id",
    "role_id,department_id",
    "department_id",
    "department_id,role_id",
    "project_id",
    "project_id,department_id",
    "project_id,resource_id",
    "project_id,role_id",
];

/**
 * @typedef {import("@web_gantt/gantt_model").Data} Data
 */

/**
 * @typedef {import("@web_gantt/gantt_model").MetaData} MetaData
 */


export class PlanningGanttModel extends GanttModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.getHighlightIds = usePlanningModelActions({
            getHighlightPlannedIds: () => this.env.searchModel.highlightPlannedIds,
            getContext: () => this.env.searchModel._context,
        }).getHighlightIds;
    }

    /**
     * @override
     */
    load(searchParams) {
        const { context, domain } = searchParams;
        this.hideOpenShift = Boolean(context.hide_open_shift);
        const displayRoleOpenShift = Boolean(context.show_role_open_shifts);
        let displayOpenShift = false;
        for (const node of domain) {
            if (
                node.length === 3 &&
                node[0] === "resource_id" &&
                ["!=", "="].includes(node[1]) &&
                node[2] === false
            ) {
                return super.load({
                    ...searchParams,
                    context: { ...context, show_job_title: true },
                });
            }
            if (
                node.length === 3 &&
                ["department_id", "manager_id", "resource_id", "job_title"].includes(node[0])
            ) {
                displayOpenShift = true;
            }
        }
        if (displayRoleOpenShift){
            searchParams.domain = Domain.and([domain, [["is_users_role", "=", true]]]).toList();
        }
        else if (displayOpenShift) {
            searchParams.domain = Domain.or([domain, "[('resource_id', '=', false)]"]).toList();
        }
        return super.load({ ...searchParams, context: { ...context, show_job_title: true } });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Object}
     */
    getAdditionalContext() {
        const { records } = this.data;
        const { startDate, scale, rangeId } = this.metaData;
        const defaultEmployeeIds = new Set();
        for (const record of records) {
            const val = record.employee_id;
            if (val) {
                defaultEmployeeIds.add(val[0]);
            }
        }
        let stopDate = this.metaData.stopDate;
        if (this.metaData.ranges && rangeId in this.metaData.ranges) {
            stopDate = localEndOf(startDate, rangeId);
        }
        return {
            ...this.searchParams.context,
            default_start_datetime: serializeDateTime(startDate),
            default_end_datetime: serializeDateTime(stopDate),
            default_slot_ids: records.map((record) => record.id),
            scale: scale.id,
            active_domain: this.getDomain(),
            active_ids: records,
            default_employee_ids: [...defaultEmployeeIds],
        };
    }

    /**
     * @override
     */
    getDialogContext() {
        const context = super.getDialogContext(...arguments);
        delete context.show_job_title;
        delete context.highlight_planned;
        delete context.highlight_conflicting;
        if (this.metaData.scale.id == 'day') {
            context.planning_keep_default_datetime = true;
        }
        return context;
    }

    /**
     * @returns {any[]}
     */
    getDomain() {
        const metaData = this._buildMetaData();
        return this._getDomain(metaData);
    }

    /**
     * @override
     */
    getSchedule(params = {}) {
        const result = super.getSchedule(params);
        if (params.recurrence_update) {
            result.recurrence_update = params.recurrence_update;
        }
        return result;
    }

    /**
     * @override
     */
    removeRedundantData(data, ids) {
        const result = super.removeRedundantData(data, ids);
        if (data.recurrence_update) {
            result.recurrence_update = data.recurrence_update;
        }
        return result;
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * Check if the given groupedBy includes fields for which an empty fake group will be created
     *
     * @protected
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowCreateEmptyGroups(groupedBy) {
        return groupedBy.includes("resource_id");
    }

    /**
     * Check if the given groupBy is in the list that has to generate empty lines
     *
     * @protected
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowedEmptyGroups(groupedBy) {
        return GROUPBY_COMBINATIONS.includes(groupedBy.join(","));
    }

    /**
     * @override
     */
    async _fetchData() {
        const [ highlightIds, ] = await Promise.all([
            this.getHighlightIds(),
            super._fetchData(...arguments),
        ])
        const firstRow = this.data?.rows?.[0];
        if (firstRow.isGroup && this.orm.isSample && !this.isClosed(firstRow.id)) {
            this.closedRows.add(firstRow.id);
        }
        this.highlightIds = highlightIds;
    }

    /**
     * @override
     */
    _fetchDataPostProcess(metaData, data) {
        const proms = [super._fetchDataPostProcess(...arguments)];
        if (data.records.length && !this.orm.isSample) {
            proms.push(this._fetchResourceWorkInterval(metaData, data));
        }
        return Promise.all(proms);
    }

    /**
     * Fetch resources' work intervals.
     * set key "workIntervals" in data
     * @param {MetaData} metaData
     * @param {Data} data
     */
    async _fetchResourceWorkInterval(metaData, data) {
        const [workIntervals, isFlexibleHours, avgWorkHours] = await this.orm.call(
            metaData.resModel,
            "gantt_resource_work_interval",
            [data.records.map((r) => r.id)],
            {
                context: {
                    ...this.searchParams.context,
                    default_start_datetime: serializeDateTime(metaData.globalStart),
                    default_end_datetime: serializeDateTime(metaData.globalStop),
                    current_scale: metaData.scale.id,
                }
            }
        );
        data.workIntervals = {};
        for (const resourceId in workIntervals) {
            const resourceIntervals = [];
            for (const workInterval of workIntervals[resourceId]) {
                resourceIntervals.push(workInterval.map(deserializeDateTime));
            }
            if (resourceIntervals.length) {
                data.workIntervals[resourceId] = resourceIntervals;
            }
        }
        data.isFlexibleHours = isFlexibleHours;
        data.avgWorkHours = avgWorkHours;
    }

    /**
     * @override
     */
    _generateRows(metaData, params) {
        const { groupedBy, groups, parentGroup } = params;
        if (!this.hideOpenShift) {
            if (parentGroup.length === 0) {
                // _generateRows is a recursive function.
                // Here, we are generating top level rows.
                if (this._allowCreateEmptyGroups(groupedBy)) {
                    // The group with false values for every groupby can be absent from
                    // groups (= groups returned by read_group basically).
                    // Here we add the fake group {} in groups in any case (this simulates the group
                    // with false values mentionned above).
                    // This will force the creation of some rows with resId = false
                    // (e.g. 'Open Shifts') from top level to bottom level.
                    groups.push({});
                }
                if (this._allowedEmptyGroups(groupedBy)) {
                    params.addOpenShifts = true;
                }
            }
            if (params.addOpenShifts && groupedBy.length === 1) {
                // Here we are generating some rows on last level under a common
                // "parent" (if any: first level can be last level).
                // We make sure that a row with resId = false for
                // the unique groupby in groupedBy and same "parent" will be
                // added by adding a suitable fake group to the groups (a subset
                // of the groups returned by read_group).
                const fakeGroup = Object.assign({}, ...parentGroup);
                groups.push(fakeGroup);
            }
        }
        const rows = super._generateRows(...arguments);
        // keep empty row to the head and sort the other rows alphabetically
        if (rows.length > 1) {
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
    _getGroupedBy(metaData, searchParams) {
        let groupBy = [...searchParams.groupBy];
        if (!this.firstLoad && searchParams.context.planning_groupby_role && !groupBy.length) {
            groupBy = ["role_id", "resource_id"];
        }
        return super._getGroupedBy(metaData, { ...searchParams, groupBy });
    }

    /**
     * @override
     */
    _getInitialRangeParams(metaData) {
        let { focusDate, scaleId, startDate, stopDate, rangeId } = super._getInitialRangeParams(...arguments);
        // take parameters from url if set https://example.com/web?date_start=2020-11-08
        // this is used by the mail of planning.planning
        const urlState = router.current;
        if (urlState.date_start) {
            focusDate = deserializeDateTime(urlState.date_start);
            if (urlState.date_end) {
                const end = deserializeDateTime(urlState.date_end);
                if (localStartOf(focusDate, "week").equals(localStartOf(end, "week"))) {
                    ({ startDate, stopDate, rangeId } = getRangeFromDate("week", focusDate));
                    scaleId = metaData.ranges[rangeId].scaleId;
                } else if (localStartOf(focusDate, "month").equals(localStartOf(end, "month"))) {
                    ({ startDate, stopDate, rangeId } = getRangeFromDate("month", focusDate));
                    scaleId = metaData.ranges[rangeId].scaleId;
                } else {
                    startDate = focusDate;
                    stopDate = end;
                    rangeId = "custom";
                }
            } else {
                const { unit } = metaData.scales[scaleId];
                ({ startDate, stopDate, rangeId } = getRangeFromDate(unit, focusDate));
            }
        }
        return { focusDate, scaleId, startDate, stopDate, rangeId };
    }

    /**
     * Rename 'Undefined Resource' and 'Undefined Department' to 'Open Shifts'.
     *
     * @override
     */
    _getRowName(_, groupedByField, value) {
        if (["department_id", "resource_id"].includes(groupedByField)) {
            const resId = Array.isArray(value) ? value[0] : value;
            if (!resId) {
                return _t("Open Shifts");
            }
        }
        return super._getRowName(...arguments);
    }

    /**
     * @override
     */
    _scheduleToData(schedule) {
        const allowedFields = [
            'recurrence_update',
            this.metaData.dateStartField,
            this.metaData.dateStopField,
            ...this.metaData.groupedBy,
        ];
        return pick(schedule, ...allowedFields);
    }
}
