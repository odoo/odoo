import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AttendanceActionHelper } from "@hr_attendance/views/attendance_helper_view";
import { AttendanceControlPanel } from "@hr_attendance/components/attendance_dashboard/attendance_control_panel";
import { AttendanceDashboard } from "@hr_attendance/components/attendance_dashboard/attendance_dashboard";

export class AttendanceKanbanController extends KanbanController {
    static template = "hr_attendance.AttendanceKanbanController";
    static components = { ...KanbanController.components, AttendanceDashboard };
}

export class AttendanceKanbanRenderer extends KanbanRenderer {
    static template = "hr_attendance.AttendanceKanbanRenderer";
    static components = {
        ...AttendanceKanbanRenderer.components,
        AttendanceActionHelper,
    };
}

export const attendanceKanbanView = {
    ...kanbanView,
    Controller: AttendanceKanbanController,
    ControlPanel: AttendanceControlPanel,
    Renderer: AttendanceKanbanRenderer,
};

registry.category("views").add("attendance_kanban_view", attendanceKanbanView);
