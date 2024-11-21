/** @odoo-module */

import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { useService } from "@web/core/utils/hooks";

export class ProjectProjectKanbanHeader extends KanbanHeader {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async deleteGroup() {
        if (this.group.groupByField.name === 'stage_id') {
            const action = await this.group.model.orm.call(
                this.group.groupByField.relation,
                'unlink_wizard',
                [this.group.value],
                { context: this.group.context },
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup();
    }
}

