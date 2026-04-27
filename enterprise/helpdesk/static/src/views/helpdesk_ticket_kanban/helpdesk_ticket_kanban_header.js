/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { KanbanHeader } from "@web/views/kanban/kanban_header";

export class HelpdeskTicketKanbanHeader extends KanbanHeader {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "sla_deadline") {
            return _t("Deadline reached");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }

    async deleteGroup() {
        if (this.group.groupByField.name === "stage_id") {
            const action = await this.group.model.orm.call(
                this.group.groupByField.relation,
                "action_unlink_wizard",
                [this.group.value],
                { context: this.group.context }
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup();
    }
}
