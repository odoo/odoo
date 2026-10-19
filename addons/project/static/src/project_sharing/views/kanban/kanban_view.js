import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { ProjectTaskRelationalModel } from "@project/views/project_task_relational_model";
import { ProjectTaskControlPanel } from "@project/views/project_task_control_panel/project_task_control_panel";

export class ProjectSharingTaskKanbanModel extends ProjectTaskRelationalModel {
    async _webReadGroup(config) {
        config.context = {
            ...config.context,
            project_kanban: true,
        };
        return super._webReadGroup(...arguments);
    }
}

patch(KanbanHeader.prototype, {
    canQuickCreate() {
        return super.canQuickCreate() && Boolean(session.portal_can_advanced_edit);
    },
});

kanbanView.ControlPanel = ProjectTaskControlPanel;
kanbanView.Model = ProjectSharingTaskKanbanModel;
