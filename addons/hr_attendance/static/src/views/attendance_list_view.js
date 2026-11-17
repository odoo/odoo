import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { AttendanceActionHelper } from "@hr_attendance/views/attendance_helper_view";
import { AttendanceControlPanel } from "@hr_attendance/components/attendance_dashboard/attendance_control_panel";
import { AttendanceDashboard } from "@hr_attendance/components/attendance_dashboard/attendance_dashboard";

export class AttendanceListController extends ListController {
    static template = "hr_attendance.AttendanceListController";
    static components = { ...ListController.components, AttendanceDashboard };
}

export class AttendanceListRenderer extends ListRenderer {
    static template = "hr_attendance.AttendanceListRenderer";
    static components = {
        ...AttendanceListRenderer.components,
        AttendanceActionHelper,
    };

    /** @override **/
    get showNoContentHelper() {
        // Rows's length need to be lower than 6 to avoid nocontent overlapping
        return super.showNoContentHelper && this.props.list.count < 6;
    }
}

export const attendanceListView = {
    ...listView,
    Controller: AttendanceListController,
    ControlPanel: AttendanceControlPanel,
    Renderer: AttendanceListRenderer,
};

registry.category("views").add("attendance_list_view", attendanceListView);
