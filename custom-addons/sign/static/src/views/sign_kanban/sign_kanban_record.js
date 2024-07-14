/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class SignKanbanRecord extends KanbanRecord {
    /**
     * @override
     * Prevent opening record for mobile views
     */
    onGlobalClick() {
        if (this.props.record.resModel === "sign.template" && this.env.isSmall) {
            return;
        }
        return super.onGlobalClick(...arguments);
    }
}
