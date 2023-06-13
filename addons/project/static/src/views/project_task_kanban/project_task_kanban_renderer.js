/** @odoo-module */

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { ProjectTaskKanbanRecord } from './project_task_kanban_record';
import { ProjectTaskKanbanHeader } from './project_task_kanban_header';
import { useService } from '@web/core/utils/hooks';

export class ProjectTaskKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.action = useService('action');

    }

    canCreateGroup() {
        return (super.canCreateGroup() && this.isProjectTasksContext() && this.props.list.isGroupedByStage) || this.props.list.isGroupedByPersonalStages;
    }

    isProjectTasksContext() {
        return this.props.list.context.active_model === "project.project" && this.props.list.context.default_project_id;
    }
}

ProjectTaskKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: ProjectTaskKanbanRecord,
    KanbanHeader: ProjectTaskKanbanHeader,
};
