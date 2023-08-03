/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

import { Record } from "@web/views/record";
import { KanbanMany2ManyTagsAvatarUserField } from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { Field } from "@web/views/fields/field";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class SubtaskKanbanList extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.subTasksRead = [];
        this.subTaskClosed = new Set();
    }

    get list() {
        return this.props.record.data.child_ids;
    }

    async goToSubtask(subtask_id) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.list.resModel,
            res_id: subtask_id,
            views: [[false, "form"]],
            target: "current",
            context: {
                active_id: subtask_id,
            },
        });
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
};

registry.category("view_widgets").add("subtask_kanban_list", subtaskKanbanList);
