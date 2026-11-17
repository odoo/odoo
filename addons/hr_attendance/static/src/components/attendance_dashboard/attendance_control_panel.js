import { ControlPanel } from "@web/search/control_panel/control_panel";

/**
 * The control panel of the attendance views, with the counters below the search bar. The views
 * pass the counters in the slot "attendance-dashboard", so they stay on top while the records
 * scroll.
 */
export class AttendanceControlPanel extends ControlPanel {
    static template = "hr_attendance.AttendanceControlPanel";
}
