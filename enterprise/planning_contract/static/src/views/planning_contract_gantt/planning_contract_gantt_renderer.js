import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";
import { patch } from "@web/core/utils/patch";

patch(PlanningGanttRenderer.prototype, {
    /**
     * @override
     */
    ganttCellAttClass(row, column) {
        return {
            ...super.ganttCellAttClass(...arguments),
            o_resource_has_no_working_periods: !this._resourceHasWorkingPeriods(column, row),
        };
    },

    /**
     * @param {number} column - Column index
     * @param {Row} row - Row Object
     */
    _resourceHasWorkingPeriods(column, row) {
        const { workingPeriods } = row;
        const { interval } = this.model.metaData.scale;
        const { start, stop } = column;
        if (workingPeriods?.length) {
            return workingPeriods.some(
                (workingPeriod) =>
                    workingPeriod.start.startOf(interval) <= start.startOf(interval) &&
                    (!workingPeriod.end ||
                        workingPeriod.end.startOf(interval) >= stop.startOf(interval))
            );
        }
        return workingPeriods === undefined;
    },

    /**
     * @override
     */
    processRow(row) {
        const { workingPeriods } = row;
        const result = super.processRow(...arguments);
        if (workingPeriods && result.rows[0]) {
            result.rows[0].workingPeriods = workingPeriods;
        }
        return result;
    },
});
