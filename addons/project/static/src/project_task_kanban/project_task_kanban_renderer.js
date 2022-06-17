/** @odoo-module */

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class ProjectTaskKanbanRenderer extends KanbanRenderer {
    async deleteGroup(group) {
        if (group && group.groupByField.name === 'stage_id') {
            const action = await group.model.orm.call(group.resModel, 'unlink_wizard', [group.resId]);
            this.action.doAction(action);
            return;
        }
        super.deleteGroup(group);
    }
}
