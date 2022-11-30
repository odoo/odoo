/** @odoo-module */

import { useService } from '@web/core/utils/hooks';

import { registry } from "@web/core/registry";
import { Component } from '@odoo/owl';
import { Record } from '@web/views/record';
import { KanbanMany2ManyTagsAvatarUserField } from "@mail/views/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { Field } from "@web/views/fields/field";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class SubtaskKanbanList extends Component {

    setup() {
        this.actionService = useService("action");
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
                fieldsToFetch: {
                    display_name: { type: "char" },
                    kanban_state: { selection: [['normal', 'In Progress'], ['done', 'Ready'], ['blocked', 'Blocked']],
                                    string: "Status",
                                    type: "selection",
                                    field: this.props.record.activeFields.kanban_state.field,
                                    attrs: this.props.record.activeFields.kanban_state.attrs,
                                    options: this.props.record.activeFields.kanban_state.options },
                    legend_blocked: { type: "char" },
                    legend_done: { type: "char" },
                    legend_normal: { type: "char" },
                    user_ids: { type: "many2many",
                                relation: "res.users",
                                field: this.props.record.activeFields.user_ids.field,
                                fieldsToFetch: this.props.record.activeFields.user_ids.fieldsToFetch,
                                attrs: this.props.record.activeFields.user_ids.attrs,
                                options: this.props.record.activeFields.user_ids.options },
                }
            }
        };
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
SubtaskKanbanList.template = 'project.SubtaskKanbanList';
const subtaskKanbanList = {
    component: SubtaskKanbanList,
    fieldDependencies: [{ name: "child_ids", type: "one2many" }],
};

registry.category("view_widgets").add("subtask_kanban_list", subtaskKanbanList);
