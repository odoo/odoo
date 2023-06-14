/** @odoo-module */

import { KanbanDynamicGroupList } from "@web/views/kanban/kanban_model";
import { Domain } from '@web/core/domain';
import { session } from '@web/session';

export class ProjectTaskKanbanDynamicGroupList extends KanbanDynamicGroupList {
    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === 'stage_id';
    }

    get isGroupedByPersonalStages() {
        return !!this.groupByField && this.groupByField.name === 'personal_stage_type_id';
    }
}
