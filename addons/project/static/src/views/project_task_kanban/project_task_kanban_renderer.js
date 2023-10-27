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

    get canMoveRecords() {
        let canMoveRecords = super.canMoveRecords;
        if (!canMoveRecords && this.canResequenceRecords && this.props.list.isGroupedByPersonalStages) {
            const { groupByField } = this.props.list;
            const { modifiers } = groupByField;
            canMoveRecords = !(modifiers && modifiers.readonly);
        }
        return canMoveRecords;
    }

    get canResequenceGroups() {
        let canResequenceGroups = super.canResequenceGroups;
        if (!canResequenceGroups && this.props.list.isGroupedByPersonalStages) {
            const { modifiers } = this.props.list.groupByField;
            const { groupsDraggable } = this.props.archInfo;
            canResequenceGroups = groupsDraggable && !(modifiers && modifiers.readonly);
        }
        return canResequenceGroups;
    }

    canCreateGroup() {
        return (super.canCreateGroup() && this.isProjectTasksContext() && this.props.list.isGroupedByStage && this.isProjectManager) || this.props.list.isGroupedByPersonalStages;
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
