/* @odoo-module */

import { formatFloatTime } from "@web/views/fields/formatters";
import { getIntersection, getUnionOfIntersections } from "@web_gantt/gantt_helpers";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { MRPWorkorderGanttRowProgressBar } from "./mrp_workorder_gantt_row_progress_bar";

const { Duration } = luxon;

export class MRPWorkorderGanttRenderer extends GanttRenderer {
    computeDerivedParams() {
        this.unavailabilities = this.model.workcentersUnavailabilities || {};
        super.computeDerivedParams();
    }

    addTo(pill, group) {
        const { start, stop } = this.subColumns[group.col - 1];
        const { date_start: otherStart, date_finished: otherStop } = pill.record;
        const interval = getIntersection(
            [start, stop.plus({ seconds: 1 })],
            [otherStart, otherStop]
        );
        let pillDuration = interval[1].diff(interval[0]);
        const workcenterId = pill.record.workcenter_id && pill.record.workcenter_id[0];
        const unavailabilities = this.unavailabilities[workcenterId] || [];
        const union = getUnionOfIntersections(interval, unavailabilities);
        for (const [otherStart, otherEnd] of union) {
            pillDuration -= otherEnd.diff(otherStart);
        }
        if (!pillDuration) {
            return false;
        }
        group.pills.push(pill);
        group.aggregateValue += pillDuration;
        return true;
    }

    getGroupPillDisplayName(pill) {
        const hours = Duration.fromMillis(pill.aggregateValue).as("hour");
        return formatFloatTime(hours);
    }

    processRow(row) {
        const { groupedByField, resId, unavailabilities } = row;
        if (groupedByField === "workcenter_id" && Boolean(unavailabilities)) {
            this.unavailabilities[resId] = unavailabilities.map((u) => [u.start, u.stop]);
        }
        return super.processRow(...arguments);
    }

    shouldComputeAggregateValues(row) {
        // compute aggregate values only for total row
        return row.id === "[]";
    }

    shouldMergeGroups() {
        return false;
    }
}

MRPWorkorderGanttRenderer.components = {
    ...GanttRenderer.components,
    GanttRowProgressBar: MRPWorkorderGanttRowProgressBar,
};
