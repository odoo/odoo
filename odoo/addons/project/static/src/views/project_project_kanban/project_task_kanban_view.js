/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProjectProjectKanbanRenderer } from "./project_project_kanban_renderer";

export const projectProjectKanbanView = {
    ...kanbanView,
    Renderer: ProjectProjectKanbanRenderer,
};

registry.category("views").add("project_project_kanban", projectProjectKanbanView);
