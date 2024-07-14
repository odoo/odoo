/** @odoo-module **/

import { GanttRowProgressBar } from "@web_gantt/gantt_row_progress_bar";

export class AttendanceGanttRowProgressBar extends GanttRowProgressBar {
    get status() {
        const {max_value, value} = this.props.progressBar;
        if (value > max_value){
            return "danger"
        }else{
            return "success"
        }
    }
}
AttendanceGanttRowProgressBar.template = "hr_attendance.AttendanceGanttRowProgressBar";
