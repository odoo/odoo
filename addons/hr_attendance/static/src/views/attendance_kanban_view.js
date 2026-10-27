import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AttendanceDashboard } from "@hr_attendance/components/attendance_dashboard/attendance_dashboard";

export class AttendanceKanbanRenderer extends KanbanRenderer {
    static template = "hr_attendance.AttendanceKanbanRenderer";
    static components = {
        ...AttendanceKanbanRenderer.components,
        AttendanceDashboard,
    };

    get showDashboard() {
        return Boolean(this.env.searchModel) && !this.env.searchModel.context.my_attendances;
    }
}

export const attendanceKanbanView = {
    ...kanbanView,
    Renderer: AttendanceKanbanRenderer,
};

registry.category("views").add("attendance_kanban_view", attendanceKanbanView);
