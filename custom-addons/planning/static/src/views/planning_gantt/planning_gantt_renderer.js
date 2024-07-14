/* @odoo-module */

import { formatFloatTime } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { getUnionOfIntersections } from "@web_gantt/gantt_helpers";
import { PlanningEmployeeAvatar } from "./planning_employee_avatar";
import { PlanningGanttRowProgressBar } from "./planning_gantt_row_progress_bar";
import { useService } from "@web/core/utils/hooks"
import { useEffect, onWillStart } from "@odoo/owl";
import { serializeDateTime } from "@web/core/l10n/dates";

const { Duration, DateTime } = luxon;

export class PlanningGanttRenderer extends GanttRenderer {
    setup() {
        super.setup();
        useEffect(() => {
            this.rootRef.el.classList.add("o_planning_gantt");
        });

        this.userService = useService('user');
        this.isPlanningManager = false;
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.isPlanningManager = await this.userService.hasGroup('planning.group_planning_manager');
    }

    /**
     * @override
     */
    addTo(pill, group) {
        if (!pill.allocatedHours[group.col]) {
            return false;
        }
        group.pills.push(pill);
        group.aggregateValue += pill.allocatedHours[group.col];
        return true;
    }

    computeDerivedParams() {
        this.rowsWithAvatar = {};
        super.computeDerivedParams();
    }

    /**
     * @override
     */
    enrichPill() {
        const pill = super.enrichPill(...arguments);
        const { record } = pill;

        const model = this.props.model;
        if (model.highlightIds && !model.highlightIds.includes(record.id)) {
            pill.className += " opacity-25";
        }
        pill.allocatedHours = {};
        const percentage = record.allocated_percentage ? record.allocated_percentage / 100 : 0;
        if (percentage === 0) {
            return pill;
        }
        if (this.isOpenShift(record) || this.isFlexibleHours(record)) {
            for (let col = this.getFirstcol(pill); col < this.getLastCol(pill) + 1; col++) {
                const subColumn = this.subColumns[col - 1];
                if (!subColumn) {
                    continue;
                }
                const { start, stop } = subColumn;
                const maxDuration = stop.diff(start);
                const toMillisRatio = 60 * 60 * 1000;
                const dailyAllocHours = Math.min(record.allocated_hours * toMillisRatio / pill.grid.column[1], maxDuration);
                if (dailyAllocHours) {
                    let minutes = Duration.fromMillis(dailyAllocHours).as("minute");
                    minutes = Math.round(minutes / 5) * 5;
                    pill.allocatedHours[col] = Duration.fromObject({ minutes }).as("hour");
                }
            }
            return pill;
        }
        const recordIntervals = this.getRecordIntervals(record);
        if (!recordIntervals.length) {
            return pill;
        }
        for (let col = this.getFirstcol(pill) - 1; col <= this.getLastCol(pill) + 1; col++) {
            const subColumn = this.subColumns[col - 1];
            if (!subColumn) {
                continue;
            }
            const { start, stop } = subColumn;
            const interval = [start, stop.plus({ seconds: 1 })];
            const union = getUnionOfIntersections(interval, recordIntervals);
            let duration = 0;
            for (const [otherStart, otherEnd] of union) {
                duration += otherEnd.diff(otherStart);
            }
            if (duration) {
                let minutes = Duration.fromMillis(duration * percentage).as("minute");
                minutes = Math.round(minutes / 5) * 5;
                pill.allocatedHours[col] = Duration.fromObject({ minutes }).as("hour");
            }
        }
        return pill;
    }

    getAvatarProps(row) {
        return this.rowsWithAvatar[row.id];
    }

    /**
     * @override
     */
    getAggregateValue(group, previousGroup) {
        return group.aggregateValue + previousGroup.aggregateValue;
    }

    /**
     * @override
     */
    getColumnStartStop(columnStartIndex, columnStopIndex = columnStartIndex) {
        const { scale } = this.model.metaData;
        if (["week", "month"].includes(scale.id)) {
            const { start } = this.columns[columnStartIndex];
            const { stop } = this.columns[columnStopIndex];
            return {
                start: start.set({ hours: 8, minutes: 0, seconds: 0 }),
                stop: stop.set({ hours: 17, minutes: 0, seconds: 0 }),
            };
        }
        return super.getColumnStartStop(...arguments);
    }

    /**
     * @override
     */
    getGroupPillDisplayName(pill) {
        return formatFloatTime(pill.aggregateValue);
    }

    /**
     * @override
     */
    getPopoverProps(pill) {
        const popoverProps = super.getPopoverProps(pill);
        if (this.popoverTemplate) {
            const { record } = pill;
            Object.assign(popoverProps.context, {
                allocatedHoursFormatted:
                    record.allocated_hours && formatFloatTime(record.allocated_hours),
                allocatedPercentageFormatted:
                    record.allocated_percentage && formatFloat(record.allocated_percentage),
            });
        }
        return popoverProps;
    }

    /**
     * @param {RelationalRecord} record
     * @returns {any[]}
     */
    getRecordIntervals(record) {
        const val = record.resource_id;
        const resourceId = Array.isArray(val) ? val[0] : false;
        const startTime = record.start_datetime;
        const endTime = record.end_datetime;
        if (!this.model.data.workIntervals) {
            return [];
        }
        const resourceIntervals = this.model.data.workIntervals[resourceId];
        if (!resourceIntervals) {
            return [];
        }
        const recordIntervals = getUnionOfIntersections([startTime, endTime], resourceIntervals);
        return recordIntervals;
    }

    /**
     * @param {RelationalRecord} record
     * @returns {boolean}
     */
    isFlexibleHours(record) {
        return !!this.model.data.isFlexibleHours?.[record.resource_id && record.resource_id[0]];
    }

    /**
     * @param {RelationalRecord} record
     * @returns {boolean}
     */
    isOpenShift(record) {
        return !record.resource_id;
    }

    hasAvatar(row) {
        return row.id in this.rowsWithAvatar;
    }

    /**
     * @override
     */
    isDisabled(row) {
        if (!row.fromServer) {
            return false;
        }
        return super.isDisabled(...arguments);
    }

    /**
     * @override
     */
    isHoverable(row) {
        if (!row.fromServer) {
            return !row.isGroup;
        }
        return super.isHoverable(...arguments);
    }

    processRow(row) {
        const { fromServer, groupedByField, name, progressBar } = row;
        const isGroupedByResource = groupedByField === "resource_id";
        const employeeId = progressBar && progressBar.employee_id;
        const employeeModel = progressBar && progressBar.employee_model;
        const isResourceMaterial = progressBar && progressBar.is_material_resource;
        const showEmployeeAvatar =
            !isResourceMaterial && isGroupedByResource && fromServer && Boolean(employeeId);
        if (showEmployeeAvatar) {
            const { fields } = this.model.metaData;
            const resModel = employeeModel || fields.employee_id.relation;
            this.rowsWithAvatar[row.id] = { resModel, resId: employeeId, displayName: name };
        }
        return super.processRow(...arguments);
    }

    /**
     * @override
     */
    shouldMergeGroups() {
        return false;
    }

    /**
     * @param {MouseEvent} ev
     * @param {Pill} pill
     * @param {number} splitIndex - Index of the split tool used on the pill
     */
    async onPillSplitToolClicked(ev, pill, splitIndex) {
        if (!this.isPlanningManager) {
            return;
        }
        const pillStart = pill.grid.column[0];

        // 1. Create a copy of the current pill after the split tool
        const startColumnId = pillStart + splitIndex;
        const { start } = this.getColumnAvailabilitiesLimit(pill, startColumnId, {
            fixed_stop: pill.record.end_datetime,
        });
        const values = { start_datetime: serializeDateTime(start) };
        const context = { planning_split_tool: true };
        await this.model.orm.call(
            this.model.metaData.resModel,
            'copy',
            [pill.record.id, values],
            { context },
        );

        // 2. Reduce the size of the current pill down to the split tool
        const { stop } = this.getColumnAvailabilitiesLimit(pill, startColumnId - 1, {
            fixed_start: pill.record.start_datetime,
        });
        const schedule = { end_datetime: serializeDateTime(stop) };
        this.model.reschedule(pill.record.id, schedule, this.openPlanDialogCallback);
    }

    /**
     * Determines the earliest (in start) and latest (in stop) availability in a column for the row of a given pill.
     * If a fixed start/stop is set, the latest/earliest availability as to be after/before it. If the row shows no
     * availability respecting the given constraint, the returned start/stop allows to create a shift of 1 second.
     *
     * @param {Pill} pill
     * @param {number} column - Column index
     * @param {{ Datetime, Datetime }} { fixed_start, fixed_stop } - If set, indicates a fixed value for the start/stop result
     * @returns {{ Datetime, Datetime }} { start, stop }
     */
    getColumnAvailabilitiesLimit(pill, column, { fixed_start, fixed_stop } = {}) {
        const defaultColumnTiming = super.getColumnStartStop(column);
        let start = fixed_start || defaultColumnTiming.start;
        let stop = fixed_stop || defaultColumnTiming.stop;
        const currentRow = this.model.data.rows.find(row => row.resId === pill.record.resource_id[0]) || this.model.data.rows.find(row => row.resId === false);

        const unavailability_at_start = currentRow?.unavailabilities?.find(unavailability => start >= unavailability.start && start < unavailability.stop);
        const unavailability_at_stop = currentRow?.unavailabilities?.find(unavailability => stop > unavailability.start && stop <= unavailability.stop);

        if (!fixed_stop && unavailability_at_stop) {
            stop = unavailability_at_stop.start;
        }
        if (!fixed_start && unavailability_at_start && stop > start) {
            start = unavailability_at_start.stop;
        }
        if (stop <= start) {
            if (!fixed_start) {
                start = DateTime.fromMillis(stop - 1000);
            } else {
                stop = DateTime.fromMillis(start + 1000);
            }
        }
        return { start, stop };
    }


}
PlanningGanttRenderer.rowHeaderTemplate = "planning.PlanningGanttRenderer.RowHeader";
PlanningGanttRenderer.pillTemplate = "planning.PlanningGanttRenderer.Pill";
PlanningGanttRenderer.components = {
    ...GanttRenderer.components,
    Avatar: PlanningEmployeeAvatar,
    GanttRowProgressBar: PlanningGanttRowProgressBar,
};
