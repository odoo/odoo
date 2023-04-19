/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { Record } from "@web/views/record";
import { KanbanMany2ManyTagsAvatarUserField } from "@mail/views/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { Field } from "@web/views/fields/field";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class SubtaskKanbanList extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.subTaskIds = [];

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.subTaskIds = await this.orm.search(this.props.record.resModel, [
            ["parent_id", "=", this.props.record.resId],
            ["state", "not in", ["1_done", "1_canceled"]],
        ]);
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

    get fieldsInfo() {
        return {
            child_ids: {
                type: "one2many",
                relation: "project.task",
                relatedFields: {
                    display_name: { type: "char" },
                    project_id: {
                        type: "many2one",
                        relation: "project.project",
                        field: this.props.record.activeFields.project_id.field,
                        relatedFields: this.props.record.activeFields.project_id.relatedFields,
                        attrs: this.props.record.activeFields.project_id.attrs,
                        options: this.props.record.activeFields.project_id.options,
                    },
                    state: {
                        selection: [
                            ["01_in_progress", "In Progress"],
                            ["02_changes_requested", "Changes Requested"],
                            ["03_approved", "Approved"],
                            ["04_waiting_normal", "Waiting"],
                            ["1_done", "Done"],
                            ["1_canceled", "Canceled"],
                        ],
                        string: "Status",
                        type: "selection",
                        field: this.props.record.activeFields.state.field,
                        viewType: this.props.record.activeFields.state.viewType,
                        attrs: this.props.record.activeFields.state.attrs,
                        options: this.props.record.activeFields.state.options,
                    },
                    user_ids: {
                        type: "many2many",
                        relation: "res.users",
                        field: this.props.record.activeFields.user_ids.field,
                        relatedFields: this.props.record.activeFields.user_ids.relatedFields,
                        attrs: this.props.record.activeFields.user_ids.attrs,
                        options: this.props.record.activeFields.user_ids.options,
                    },
                },
            },
        };
    }

    get values() {
        return { child_ids: this.subTaskIds };
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
