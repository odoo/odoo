/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AppointmentTypeKanbanRecord } from "@appointment/views/kanban/kanban_record";

export class AppointmentTypeKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: AppointmentTypeKanbanRecord,
    };
}
