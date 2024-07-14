/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SignKanbanRecord } from "@sign/views/sign_kanban/sign_kanban_record";

export class SignKanbanRenderer extends KanbanRenderer {
    /**
     * @override
     * Prevent moving records for sign request items
     */
    get canMoveRecords() {
        return super.canMoveRecords && this.props.list.resModel !== "sign.request";
    }

    /**
     * @override
     * Prevent moving groups for sign request items
     */
    get canResequenceGroups() {
        return super.canResequenceGroups && this.props.list.resModel !== "sign.request";
    }
}
SignKanbanRenderer.component = {
    ...KanbanRenderer.components,
    KanbanRecord: SignKanbanRecord,
};
