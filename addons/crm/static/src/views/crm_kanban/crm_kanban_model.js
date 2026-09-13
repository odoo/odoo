import { checkRainbowmanMessage } from "@crm/views/check_rainbowman_message";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export class CrmKanbanModel extends RelationalModel {
    setup(params, { effect }) {
        super.setup(...arguments);
        this.effect = effect;
    }
}

export class CrmKanbanDynamicGroupList extends RelationalModel.DynamicGroupList {
    /**
     * @override
     *
     * If the kanban view is grouped by stage_id check if the lead is won and display
     * a rainbowman message if that's the case.
     */
    async moveRecords(recordIds, refId, targetGroupId) {
        const targetGroup = this.groups.find((group) => group.id === targetGroupId);
        // the leads that change stage, i.e. the ones not already in the target group
        const movedLeads = this.records.filter(
            (r) => recordIds.includes(r.id) && r.group !== targetGroup
        );

        await super.moveRecords(...arguments);

        if (targetGroup && movedLeads.length && this.groupByField.name === "stage_id") {
            // a single message, even when several leads were moved at once
            await checkRainbowmanMessage(this.model.orm, this.model.effect, movedLeads[0].resId);
        }
    }
}

CrmKanbanModel.DynamicGroupList = CrmKanbanDynamicGroupList;
CrmKanbanModel.services = [...RelationalModel.services, "effect"];
