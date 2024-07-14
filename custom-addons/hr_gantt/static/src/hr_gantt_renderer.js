/* @odoo-module */

import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { GanttRenderer } from "@web_gantt/gantt_renderer";

const { DateTime } = luxon;

export class HrGanttRenderer extends GanttRenderer {
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
     * Returns the colmn index closest to the given date and their diff in hours
     * @param {DateTime} date
     * @returns {[number, number]}
     */
    closestDateGridColumn(date) {
        const dates = this.dateGridColumns;
        let [left, right] = [0, dates.length - 1];
        let mid, diff;
        while (left <= right) {
            mid = Math.floor((left + right) / 2);
            diff = date.ts - dates[mid].ts;
            if (Math.abs(diff) >= Math.abs(date.ts - dates[mid - 1]?.ts)) {
                right = mid - 1;
            } else if (Math.abs(diff) > Math.abs(date.ts - dates[mid + 1]?.ts)) {
                left = mid + 1;
            } else {
                break;
            }
        }
        return [mid, diff / 3.6e+6];
    }

    /**
     * @param {RelationalRecord} record
     * @returns {Partial<Pill>}
     */
    getPill(record) {
        const pill = super.getPill(record);
        switch (this.model.metaData.scale.id) {
            case "week":
            case "month": {
                const {
                    dateStartField,
                    dateStopField,
                    startDate,
                    stopDate,
                } = this.model.metaData;
                const pillStartDate = DateTime.max(startDate, record[dateStartField]);
                const pillStopDate = DateTime.min(stopDate, record[dateStopField]);

                let [startIndex, diffStart] = this.closestDateGridColumn(pillStartDate);
                let [stopIndex, diffStop] = this.closestDateGridColumn(pillStopDate);

                if (startIndex === stopIndex) {
                    if (diffStart < -2 && diffStop > 2) {
                        startIndex -= 1;
                        stopIndex += 1;
                    } else if (diffStart < 0) {
                        startIndex -= 1;
                    } else {
                        stopIndex += 1;
                    }
                } else {
                    if (diffStart < -2) {
                        startIndex -= 1;
                    }
                    if (diffStop > 2) {
                        stopIndex += 1;
                    }
                }

                const firstCol = startIndex + 1;
                const span = stopIndex - startIndex;
                pill.grid = { column: [firstCol, span] };
                pill.startDate = this.dateGridColumns[startIndex];
                pill.stopDate = this.dateGridColumns[stopIndex];
            }
        }
        return pill;
    }
}

HrGanttRenderer.rowHeaderTemplate = "hr.HrGanttRenderer.RowHeader";
HrGanttRenderer.components = { ...GanttRenderer.components, Avatar };
