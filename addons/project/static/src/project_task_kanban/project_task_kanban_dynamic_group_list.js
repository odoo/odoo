/** @odoo-module */

import { KanbanDynamicGroupList } from "@web/views/kanban/kanban_model";

export class ProjectTaskKanbanDynamicGroupList extends KanbanDynamicGroupList {
    get context() {
        const context = super.context;
        if (context.createPersonalStageGroup) {
            context.default_user_id = context.uid;
            delete context.createPersonalStageGroup;
            delete context.default_project_id;
        }
        return context;
    }

    async createGroup() {
        const isGroupedByPersonalStages = this.groupByField.name === 'personal_stage_type_ids';
        if (isGroupedByPersonalStages) {
            this.defaultContext = Object.assign({}, this.defaultContext || {}, {
                createPersonalStageGroup: true,
            });
        }
        const result = await super.createGroup(...arguments);
        if (isGroupedByPersonalStages) {
            delete this.defaultContext.createPersonalStageGroup;
        }
        return result;
    }
}
