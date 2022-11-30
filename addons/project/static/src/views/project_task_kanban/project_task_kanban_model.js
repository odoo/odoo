/** @odoo-module */

import { KanbanModel } from "@web/views/kanban/kanban_model";

import { ProjectTaskKanbanDynamicGroupList } from "./project_task_kanban_dynamic_group_list";
import { Record } from '@web/views/relational_model';

export class ProjectTaskRecord extends Record {
    async _applyChanges(changes) {
        const value = changes.personal_stage_type_ids;
        if (Array.isArray(value)) {
            delete changes.personal_stage_type_ids;
            changes.personal_stage_type_id = value;
        }
        await super._applyChanges(changes);
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

export class ProjectTaskKanbanGroup extends KanbanModel.Group {
    get isPersonalStageGroup() {
        return !!this.groupByField && this.groupByField.name === 'personal_stage_type_ids';
    }

    async delete() {
        if (this.isPersonalStageGroup) {
            this.deleted = true;
            return await this.model.orm.call(this.resModel, 'remove_personal_stage', [this.resId]);
        } else {
            return await super.delete();
        }
    }
}

export class ProjectTaskKanbanModel extends KanbanModel { }

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
ProjectTaskKanbanModel.Group = ProjectTaskKanbanGroup;
ProjectTaskKanbanModel.Record = ProjectTaskRecord;
