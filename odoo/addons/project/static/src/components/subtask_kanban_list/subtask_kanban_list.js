/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

import { Record } from "@web/model/record";
import { KanbanMany2ManyTagsAvatarUserField } from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { Field, getFieldFromRegistry } from "@web/views/fields/field";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class SubtaskKanbanList extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.subTasksRead = [];
        this.subTaskClosed = new Set();

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.subTasksRead = await this.orm.searchRead(
            this.props.record.resModel, [
                ["parent_id", "=", this.props.record.resId],
                ["state", "not in", ["1_done", "1_canceled"]],
            ],
            this.fieldNames
        );
    }

    async goToSubtask(subtask_id) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.props.record.resModel,
            res_id: subtask_id,
            views: [[false, "form"]],
            target: "current",
            context: {
                active_id: subtask_id,
            },
        });
    }

    get fieldNames() {
        return Object.keys(this.fields);
    }

    get fields() {
        const { display_name, state, user_ids, project_id } = this.props.record.fields;
        return {
            display_name,
            state,
            user_ids,
            project_id,
        };
    }

    get activeFields() {
        return {
            display_name: {},
            state: {
                name: "state",
                viewType: "kanban",
                field: getFieldFromRegistry(this.fields.state.type, "project_task_state_selection", "kanban"),
            },
            user_ids: {
                name: "user_ids",
                field: getFieldFromRegistry(this.fields.user_ids.type, "many2many_avatar_user", "kanban"),
            },
            project_id: {
                field: getFieldFromRegistry(this.fields.project_id.type, "project", "kanban")
            },
        };
    }

    async onSubTaskSaved(subTask) {
        const ids = this.subTasksRead.map((t) => t.id);
        this.subTasksRead = await this.orm.searchRead(
            this.props.record.resModel,
            [["id", "in", ids]],
            this.fieldNames
        );
        const isKnownAsClosed = this.subTaskClosed.has(subTask.resId);
        const isClosed = subTask.data.state.startsWith("1_");
        if (isKnownAsClosed && !isClosed) {
            this.subTaskClosed.delete(subTask.resId);
        } else if (!isKnownAsClosed && isClosed) {
            this.subTaskClosed.add(subTask.resId);
        } else { // nothing to do
            return;
        }
        await this.props.record.load();
    }
}

SubtaskKanbanList.components = {
    Record,
    Field,
    KanbanMany2ManyTagsAvatarUserField,
};
SubtaskKanbanList.props = {
    ...standardWidgetProps,
};
SubtaskKanbanList.template = "project.SubtaskKanbanList";
const subtaskKanbanList = {
    component: SubtaskKanbanList,
    fieldDependencies: [{ name: "child_ids", type: "one2many" }],
};

registry.category("view_widgets").add("subtask_kanban_list", subtaskKanbanList);
