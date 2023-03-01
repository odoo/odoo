/** @odoo-module */

import { TodoKanbanRenderer } from "@note/views/todo_kanban/todo_kanban_renderer";
import { ProjectTaskKanbanRecord } from "./project_task_kanban_record";

export class ProjectTaskKanbanRenderer extends TodoKanbanRenderer {
    static components = {
        ...TodoKanbanRenderer.components,
        KanbanRecord: ProjectTaskKanbanRecord,
    };
}
