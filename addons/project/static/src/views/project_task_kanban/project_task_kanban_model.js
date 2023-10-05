/** @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ProjectTaskKanbanDynamicGroupList extends RelationalModel.DynamicGroupList {
    get context() {
        const context = { ...super.context };
        if (this.creatingPersonnalStage) {
            context.default_user_id = context.uid;
            delete context.default_project_id;
        }
        return context;
    }

    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === "stage_id";
    }

    get isGroupedByPersonalStages() {
        return !!this.groupByField && this.groupByField.name === "personal_stage_type_ids";
    }

    async createGroup(groupName, foldField) {
        if (this.isGroupedByPersonalStages) {
            return this.model.mutex.exec(async () => {
                this.creatingPersonnalStage = true;
                await this._createGroup(groupName, foldField);
                delete this.creatingPersonnalStage;
            });
        }
        return super.createGroup(...arguments);
    }

    async _unlinkGroups(groups) {
        if (this.isGroupedByPersonalStages) {
            const groupResIds = groups.map((g) => g.value);
            return this.model.orm.call("project.task.type", "remove_personal_stage", groupResIds);
        }
        return super._deleteGroups(...arguments);
    }
}

export class ProjectTaskRecord extends RelationalModel.Record {
    _update(changes, options) {
        let value = changes.personal_stage_type_ids;
        if(value){
            if (!Array.isArray(value)) {
                value = [value, false];
            }
            delete changes.personal_stage_type_ids;
            changes.personal_stage_type_id = value;
        }
        return super._update(changes, options);
    }

    get context() {
        const context = super.context;
        const value = context.default_personal_stage_type_ids;
        if (Array.isArray(value)) {
            context.default_personal_stage_type_id = value[0];
            delete context.default_personal_stage_type_ids;
        }
        return context;
    }
}

export class ProjectTaskKanbanModel extends RelationalModel {}

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
ProjectTaskKanbanModel.Record = ProjectTaskRecord;
