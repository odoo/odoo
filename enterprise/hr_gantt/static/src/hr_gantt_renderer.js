import { GanttEmployeeAvatar } from "./hr_gantt_employee_avatar";
import { GanttRenderer } from "@web_gantt/gantt_renderer";

const { DateTime } = luxon;

export class HrGanttRenderer extends GanttRenderer {
    static rowHeaderTemplate = "hr.HrGanttRenderer.RowHeader";
    static components = { ...GanttRenderer.components, Avatar: GanttEmployeeAvatar };
    computeDerivedParams() {
        this.rowsWithAvatar = {};
        super.computeDerivedParams();
    }

    getAvatarProps(row) {
        return this.rowsWithAvatar[row.id];
    }

    hasAvatar(row) {
        return row.id in this.rowsWithAvatar;
    }

    processRow(row) {
        const { groupedByField, name, resId } = row;
        if (groupedByField === "employee_id" && Boolean(resId)) {
            const { fields } = this.model.metaData;
            const relation = fields.employee_id.relation;
            const resModel = relation === 'hr.employee' ? 'hr.employee.public' : relation;
            this.rowsWithAvatar[row.id] = { resModel, resId, displayName: name };
        }
        return super.processRow(...arguments);
    }

    /**
     * Override to factor in lunch brakes between 11:00 to 14:00.
     * Stops morning or afternoon shift pills from spanning an entire day.
     *
     * @param {RelationalRecord} record
     * @returns {Partial<Pill>}
     */
    getPill(record) {
        const pill = super.getPill(record);
        const { unit } = this.model.metaData.scale;
        const [startIndex, endIndex] = pill.grid.column;
        // only check pills that span 2 half-days for in week or month views
        if (["week", "month"].includes(unit) && (endIndex - startIndex === 2)) {
            const {
                dateStartField,
                dateStopField,
                globalStart,
                globalStop,
            } = this.model.metaData;
            const start = DateTime.max(globalStart, record[dateStartField]);
            const stop = DateTime.min(globalStop, record[dateStopField]);
            if (start.day === stop.day) {
                const startTime = start.hour + (start.minute / 60);
                const stopTime = stop.hour + (stop.minute / 60);
                // we can assume startTime < 12:00 and stopTime > 12:00
                const closestToNoon = 12 - startTime < stopTime - 12 ? startTime : stopTime;
                if (startTime >= 11 && startTime === closestToNoon) {
                    // most of pill is placed in afternoon, so round off first half
                    pill.grid.column = [startIndex + 1, endIndex];
                } else if (stopTime <= 14) {
                    // start time is before 11:00 or most of pill is before noon
                    // so round off second half
                    pill.grid.column = [startIndex, endIndex - 1];
                }
            }
        }
        return pill;
    }
}
