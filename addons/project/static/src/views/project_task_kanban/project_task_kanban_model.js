/** @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ProjectTaskKanbanDynamicGroupList extends RelationalModel.DynamicGroupList {
    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === "stage_id";
    }
}

export class ProjectTaskKanbanModel extends RelationalModel {}

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
