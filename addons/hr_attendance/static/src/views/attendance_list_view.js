import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { AttendanceControlPanel } from "@hr_attendance/components/attendance_dashboard/attendance_control_panel";
import { AttendanceDashboard } from "@hr_attendance/components/attendance_dashboard/attendance_dashboard";

export class AttendanceListController extends ListController {
    static template = "hr_attendance.AttendanceListController";
    static components = { ...ListController.components, AttendanceDashboard };
}

export class AttendanceListModel extends listView.Model {
    /**
     * The attendances of the archived employees are hidden unless the search filters on the employee's active state
     * (Archived Employees filter).
     * @override
     */
    async load(params = {}) {
        const filtersEmployeeActive = params.domain?.some(
            (leaf) => Array.isArray(leaf) && leaf[0] === "employee_id.active"
        );
        if (params.domain && !filtersEmployeeActive && "employee_id" in this.config.fields) {
            params = { ...params, domain: [...params.domain, ["employee_id.active", "=", true]] };
        }
        return super.load(params);
    }
}

export const attendanceListView = {
    ...listView,
    Model: AttendanceListModel,
    Controller: AttendanceListController,
    ControlPanel: AttendanceControlPanel,
};

registry.category("views").add("attendance_list_view", attendanceListView);
