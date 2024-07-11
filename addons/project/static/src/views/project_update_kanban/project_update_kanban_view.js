/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProjectUpdateKanbanController } from './project_update_kanban_controller';

export const projectUpdateKanbanView = {
    ...kanbanView,
    Controller: ProjectUpdateKanbanController,
};

registry.category('views').add('project_update_kanban', projectUpdateKanbanView);
