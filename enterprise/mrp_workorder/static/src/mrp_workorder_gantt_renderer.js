import { formatFloatTime } from "@web/views/fields/formatters";
import { getIntersection, getUnionOfIntersections } from "@web_gantt/gantt_helpers";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { MRPWorkorderGanttRowProgressBar } from "./mrp_workorder_gantt_row_progress_bar";

const { Duration } = luxon;

export class MRPWorkorderGanttRenderer extends GanttRenderer {
    static components = {
        ...GanttRenderer.components,
        GanttRowProgressBar: MRPWorkorderGanttRowProgressBar,
    };

    addTo(pill, group) {
        const { unavailabilities } = this.model.data;
        const { start, stop } = this.getSubColumnFromColNumber(group.col);
        const { date_start: otherStart, date_finished: otherStop } = pill.record;
        const interval = getIntersection(
            [start, stop.plus({ seconds: 1 })],
            [otherStart, otherStop]
        );
        let pillDuration = interval[1].diff(interval[0]);
        const workcenterId = pill.record.workcenter_id && pill.record.workcenter_id[0];
        const workCenterUnavailabilities = (unavailabilities.workcenter_id?.[workcenterId] || []).map(({ start, stop }) => [start, stop]);
        const union = getUnionOfIntersections(interval, workCenterUnavailabilities);
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

    shouldComputeAggregateValues(row) {
        // compute aggregate values only for total row
        return row.id === "[]";
    }

    shouldMergeGroups() {
        return false;
    }
}
