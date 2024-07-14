 /** @odoo-module **/

import { HrGanttRenderer } from "@hr_gantt/hr_gantt_renderer";
 import {AttendanceGanttRowProgressBar} from "./attendance_row_progress_bar";

export class AttendanceGanttRenderer extends HrGanttRenderer {
    onPillClicked(ev, pill) {
        this.model.mutex.exec(
            () => this.props.openDialog({ resId: pill.record.id })
        )
    }
}

AttendanceGanttRenderer.components = {
    ...HrGanttRenderer.components,
    GanttRowProgressBar: AttendanceGanttRowProgressBar,
};
