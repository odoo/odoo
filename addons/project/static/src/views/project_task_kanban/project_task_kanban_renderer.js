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

    get canMoveRecords() {
        let canMoveRecords = super.canMoveRecords;
        if (!canMoveRecords && this.canResequenceRecords && this.props.list.isGroupedByPersonalStages) {
            const { groupByField } = this.props.list;
            canMoveRecords = groupByField.readonly !== "True";
        }
        return canMoveRecords;
    }

    get canResequenceGroups() {
        let canResequenceGroups = super.canResequenceGroups;
        if (!canResequenceGroups && this.props.list.isGroupedByPersonalStages) {
            const { groupsDraggable } = this.props.archInfo;
            canResequenceGroups = groupsDraggable && groupsDraggable.readonly !== "True";
        }
        return canResequenceGroups;
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
