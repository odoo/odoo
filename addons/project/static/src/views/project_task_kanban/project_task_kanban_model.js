/** @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ProjectTaskKanbanDynamicGroupList extends RelationalModel.DynamicGroupList {
    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === "stage_id";
    }
}

export class ProjectTaskKanbanModel extends RelationalModel {
    async _webReadGroup(config, firstGroupByName, orderBy) {
        config.context = {
            ...config.context,
            project_kanban: true,
        };
        return super._webReadGroup(...arguments);
    }
}

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
