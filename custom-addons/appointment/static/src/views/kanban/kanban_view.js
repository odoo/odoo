/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { AppointmentTypeKanbanRenderer } from "@appointment/views/kanban/kanban_renderer";

export const AppointmentTypeKanbanView = {
    ...kanbanView,
    Renderer: AppointmentTypeKanbanRenderer,
};
registry.category("views").add("appointment_type_kanban", AppointmentTypeKanbanView);
