/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AppointmentTypeActionHelper } from "@appointment/components/appointment_type_action_helper/appointment_type_action_helper";
import { AppointmentTypeKanbanRecord } from "@appointment/views/kanban/kanban_record";

export class AppointmentTypeKanbanRenderer extends KanbanRenderer {
    static template = "appointment.AppointmentTypeKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: AppointmentTypeKanbanRecord,
        AppointmentTypeActionHelper,
    };
}
