/** @odoo-module */

import { KanbanModel } from "@web/views/kanban/kanban_model";

import { ProjectTaskKanbanDynamicGroupList } from "./project_task_kanban_dynamic_group_list";
import { ProjectTaskRecord } from './project_task_kanban_record';

export class ProjectTaskKanbanGroup extends KanbanModel.Group {
    get isPersonalStageGroup() {
        return !!this.groupByField && this.groupByField.name === 'personal_stage_type_ids';
    }

    async delete() {
        if (this.isPersonalStageGroup) {
            return await this.model.orm.call(this.resModel, 'remove_personal_stage', [this.resId]);
        } else {
            return super.delete();
        }
    }
}

export class ProjectTaskKanbanModel extends KanbanModel { }

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
ProjectTaskKanbanModel.Group = ProjectTaskKanbanGroup;
ProjectTaskKanbanModel.Record = ProjectTaskRecord;
