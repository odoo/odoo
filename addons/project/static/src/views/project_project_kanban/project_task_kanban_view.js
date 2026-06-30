import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProjectKanbanController } from "./project_project_kanban_controller";
import { ProjectProjectKanbanRenderer } from "./project_project_kanban_renderer";
import { ProjectRelationalModel } from "../project_relational_model";

export const projectProjectKanbanView = {
    ...kanbanView,
    Controller: ProjectKanbanController,
    Renderer: ProjectProjectKanbanRenderer,
    Model: ProjectRelationalModel,
};

registry.category("views").add("project_project_kanban", projectProjectKanbanView);
