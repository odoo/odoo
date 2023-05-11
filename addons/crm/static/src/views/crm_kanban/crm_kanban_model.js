/** @odoo-module **/

import { KanbanModel } from "@web/views/kanban/kanban_model";
import { checkRainbowmanMessage } from "@crm/views/check_rainbowman_message";

export class CrmKanbanModel extends KanbanModel {
    setup(params, { effect }) {
        super.setup(...arguments);
        this.effect = effect;
    }
}

export class CrmKanbanDynamicGroupList extends CrmKanbanModel.DynamicGroupList {
    /**
     * @override
     *
     * If the kanban view is grouped by stage_id check if the lead is won and display
     * a rainbowman message if that's the case.
     */
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const succeeded = await super.moveRecord(...arguments);
        if (!succeeded) {
            return;
        }
        const sourceGroup = this.groups.find((g) => g.id === dataGroupId);
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);
        if (
            dataGroupId !== targetGroupId &&
            sourceGroup &&
            targetGroup &&
            sourceGroup.groupByField.name === "stage_id"
        ) {
            const record = targetGroup.list.records.find((r) => r.id === dataRecordId);
            await checkRainbowmanMessage(this.model.orm, this.model.effect, record.resId);
        }
    }
}

CrmKanbanModel.DynamicGroupList = CrmKanbanDynamicGroupList;
CrmKanbanModel.services = [...KanbanModel.services, "effect"];
