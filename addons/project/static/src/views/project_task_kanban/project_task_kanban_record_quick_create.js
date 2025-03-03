import { KanbanRecordQuickCreate } from "@web/views/kanban/kanban_record_quick_create";

import { ProjectTaskKanbanQuickCreateModel } from "./project_task_kanban_quick_create_model";

export class ProjectTaskKanbanRecordQuickCreate extends KanbanRecordQuickCreate {
    async getQuickCreateProps(props) {
        await super.getQuickCreateProps(props);
        this.quickCreateProps.Model = ProjectTaskKanbanQuickCreateModel;
    }
}
