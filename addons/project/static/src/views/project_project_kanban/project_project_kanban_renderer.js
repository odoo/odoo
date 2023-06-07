/** @odoo-module */

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProjectProjectKanbanHeader } from "./project_project_kanban_header";


export class ProjectProjectKanbanRenderer extends KanbanRenderer {}

ProjectProjectKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanHeader: ProjectProjectKanbanHeader,
};
