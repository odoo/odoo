/** @odoo-module */

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { ProjectTaskKanbanRecord } from './project_task_kanban_record';
import { ProjectTaskKanbanHeader } from './project_task_kanban_header';
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";

export class ProjectTaskKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.action = useService('action');
        const user = useService("user");

        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });
    }

    canCreateGroup() {
        // This restrict the creation of project stages to the kanban view of a given project
        return super.canCreateGroup() && (this.isProjectTasksContext() == this.props.list.isGroupedByStage
            && this.isProjectManager || this.props.list.groupByField.name === 'personal_stage_type_id');
    }

    isProjectTasksContext() {
        return this.props.list.context.active_model === "project.project" && !!this.props.list.context.default_project_id;
    }
}

ProjectTaskKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: ProjectTaskKanbanRecord,
    KanbanHeader: ProjectTaskKanbanHeader,
};
