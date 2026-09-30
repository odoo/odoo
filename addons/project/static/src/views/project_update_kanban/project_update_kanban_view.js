import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProjectUpdateKanbanController } from './project_update_kanban_controller';
import { ProjectRelationalModel } from "../project_relational_model";

export const projectUpdateKanbanView = {
    ...kanbanView,
    Controller: ProjectUpdateKanbanController,
    Model: ProjectRelationalModel,
};

registry.category('views').add('project_update_kanban', projectUpdateKanbanView);
