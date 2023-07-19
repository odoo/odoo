/** @odoo-module */

import { KanbanDynamicGroupList } from "@web/views/kanban/kanban_model";

export class ProjectTaskKanbanDynamicGroupList extends KanbanDynamicGroupList {
    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === 'stage_id';
    }
}
