import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { rottingKanbanView } from "@mail/js/rotting_mixin/rotting_kanban_view";
import { ProjectKanbanController, ProjectKanbanGroupStageController } from "./project_project_kanban_controller";
import { ProjectProjectKanbanRenderer, ProjectProjectKanbanGroupStageRenderer } from "./project_project_kanban_renderer";
import { ProjectRelationalModel } from "../project_relational_model";

export const projectProjectKanbanView = {
    ...kanbanView,
    Controller: ProjectKanbanController,
    Renderer: ProjectProjectKanbanRenderer,
    Model: ProjectRelationalModel,
    buttonTemplate: "project.ProjectKanbanView.Buttons",
};

export const projectProjectKanbanGroupStageView = {
    ...rottingKanbanView,
    Controller: ProjectKanbanGroupStageController,
    Renderer: ProjectProjectKanbanGroupStageRenderer,
    Model: ProjectRelationalModel,
};

registry.category("views").add("project_project_kanban", projectProjectKanbanView);
registry.category("views").add("project_project_kanban_group_stage", projectProjectKanbanGroupStageView);
