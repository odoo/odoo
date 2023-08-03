/** @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

import { Record } from "@web/model/relational_model/record";
import { makeActiveField } from "@web/model/relational_model/utils";

export class ProjectTaskRecord extends Record {
    setup() {
        super.setup(...arguments);
        this.displaySubtasks = false;
    }

    async toggleSubtasksList() {
        const { display_name, project_id, state, user_ids } = this.config.fields;
        const activeField = makeActiveField({ onChange: true });
        activeField.related = {
            activeFields: {
                display_name: makeActiveField(),
                state: makeActiveField(),
                user_ids: makeActiveField(),
                project_id: makeActiveField(),
            },
            fields: {
                display_name,
                project_id,
                state,
                user_ids,
            },
        };
        await this._load({
            activeFields: { ...this.config.activeFields, child_ids: activeField },
        });
        this.displaySubtasks = !this.displaySubtasks;
    }

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

export class ProjectTaskKanbanGroup extends RelationalModel.Group {
    get isPersonalStageGroup() {
        return !!this.groupByField && this.groupByField.name === "personal_stage_type_ids";
    }

    async delete() {
        if (this.isPersonalStageGroup) {
            this.deleted = true;
            return await this.model.orm.call(this.resModel, "remove_personal_stage", [this.resId]);
        } else {
            return await super.delete();
        }
    }
}

export class ProjectTaskKanbanModel extends RelationalModel {}

// ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
// ProjectTaskKanbanModel.Group = ProjectTaskKanbanGroup;
ProjectTaskKanbanModel.Record = ProjectTaskRecord;
