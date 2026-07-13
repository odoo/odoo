/** @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ProjectTaskKanbanDynamicGroupList extends RelationalModel.DynamicGroupList {
    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === "stage_id";
    }

    async _unlinkGroups(groups) {
        if (this.groupByField.name === "stage_id") {
            const action = await this.model.orm.call(
                this.groupByField.relation,
                'unlink_wizard',
                groups.map((g) => g.value),
                { context: this.context },
            );
            return new Promise((resolve) => {
                this.model.action.doAction(action, {
                    onClose: ({ success }) => resolve(!!success),
                });
            });
        }
        return super._unlinkGroups(groups);
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
