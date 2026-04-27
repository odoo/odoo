import { GanttRowProgressBar } from "@web_gantt/gantt_row_progress_bar";

export class AttendanceGanttRowProgressBar extends GanttRowProgressBar {
    static template = "hr_attendance.AttendanceGanttRowProgressBar";
    static props = {
        ...GanttRowProgressBar.props,
        progressBar: {
            ...GanttRowProgressBar.props.progressBar,
            shape: {
                ...GanttRowProgressBar.props.progressBar.shape,
                is_fully_flexible_hours: { type: Boolean, optional: true },
            },
        },
    };

    get status() {
        const {max_value, value} = this.props.progressBar;
        if (value > max_value){
            return "danger"
        }else{
            return "success"
        }
    }
}
