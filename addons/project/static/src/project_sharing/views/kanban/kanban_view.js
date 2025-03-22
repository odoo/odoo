/** @odoo-module */

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanDynamicGroupList, KanbanModel } from "@web/views/kanban/kanban_model";

export class ProjectSharingTaskKanbanDynamicGroupList extends KanbanDynamicGroupList {
    get context() {
        return {
            ...super.context,
            project_kanban: true,
        };
    }
}

export class ProjectSharingTaskKanbanModel extends KanbanModel {}

ProjectSharingTaskKanbanModel.DynamicGroupList = ProjectSharingTaskKanbanDynamicGroupList;

kanbanView.Model = ProjectSharingTaskKanbanModel;
