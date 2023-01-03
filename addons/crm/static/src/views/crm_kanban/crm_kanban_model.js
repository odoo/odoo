/** @odoo-module **/

import { KanbanModel } from "@web/views/kanban/kanban_model";
import { checkRainbowmanMessage } from "@crm/views/check_rainbowman_message";

export class CrmKanbanModel extends KanbanModel {
    setup(params, { orm, effect }) {
        super.setup(...arguments);
        this.ormService = orm;
        this.effect = effect;
    }
}

export class CrmKanbanDynamicGroupList extends CrmKanbanModel.DynamicGroupList {
    /**
     * @override
     *
     * Add the RRM field to the sumfields to fetch in read_group calls
     */
    get sumFields() {
        const result = super.sumFields;
        if (this.model.progressAttributes.recurring_revenue_sum_field) {
            result.push(this.model.progressAttributes.recurring_revenue_sum_field.name);
        }
        return result;
    }

    /**
     * @override
     *
     * If the kanban view is grouped by stage_id check if the lead is won and display
     * a rainbowman message if that's the case.
     */
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const res = await super.moveRecord(...arguments);
        const sourceGroup = this.groups.find((g) => g.id === dataGroupId);
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);
        if (
            dataGroupId !== targetGroupId &&
            sourceGroup &&
            targetGroup &&
            sourceGroup.groupByField.name === "stage_id"
        ) {
            const record = targetGroup.list.records.find((r) => r.id === dataRecordId);
            await checkRainbowmanMessage(this.model.ormService, this.model.effect, record.resId);
        }
        return res;
    }
}

export class CrmKanbanGroup extends CrmKanbanModel.Group {
    /**
     * This is called whenever the progress bar is changed, for example
     * when filtering on a certain stage from the progress bar and is meant
     * to update `sum_field` aggregated value.
     * We also want to update the recurring revenue aggregate.
     */
    updateAggregates(groupData) {
        if (this.model.progressAttributes.recurring_revenue_sum_field) {
            const rrField = this.model.progressAttributes.recurring_revenue_sum_field;
            const group = groupData.find(g => this.valueEquals(g[this.groupByField.name]));
            if (rrField) {
                this.aggregates[rrField.name] = group ? group[rrField.name] : 0;
            }
        }
        return super.updateAggregates(...arguments);
    }
}

CrmKanbanModel.DynamicGroupList = CrmKanbanDynamicGroupList;
CrmKanbanModel.Group = CrmKanbanGroup;
CrmKanbanModel.services = [...KanbanModel.services, "effect", "orm"];
