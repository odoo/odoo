import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { Field, getPropertyFieldInfo } from "@web/views/fields/field";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { SubtaskCreate } from "./subtask_kanban_create/subtask_kanban_create";

export class SubtaskKanbanList extends Component {
    static components = {
        Field,
        SubtaskCreate,
    };
    static props = {
        ...standardWidgetProps,
        isReadonly: {
            type: Boolean,
            optional: true,
        },
    };
    static template = "project.SubtaskKanbanList";

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.subtaskCreate = useState({
            open: false,
            name: "",
        });
        this.state = useState({
            subtasks: [],
            isLoad: true,
            prevSubtaskCount: 0,
        });
    }

    get list() {
        return this.props.record.data.child_ids;
    }

    get closedList() {
        const currentCount = this.list.records.length;
        if (this.state.isLoad || currentCount !== this.state.prevSubtaskCount) {
            this.state.prevSubtaskCount = currentCount;
            this.state.isLoad = false;
            this.state.subtasks = this.list.records
                .filter((subtask) => !["1_done", "1_canceled"].includes(subtask.data.state));
        }
        return this.state.subtasks;
    }

    get fieldInfo() {
        return {
            state: {
                ...getPropertyFieldInfo({
                    name: "state",
                    type: "selection",
                    widget: "project_task_state_selection",
                }),
                viewType: "kanban",
            },
        };
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

    async onSubTaskCreated(ev) {
        this.subtaskCreate.open = true;
    }

    async _onBlur() {
        this.subtaskCreate.open = false;
    }

    async _onSubtaskCreateNameChanged(name) {
        if (name.trim() === "") {
            this.notification.add(_t("Invalid Display Name"), {
                type: "danger",
            });
        } else {
            const sequences = this.list.records.map(r => r.data.sequence);
            const nextSequence = (sequences.length ? Math.max(...sequences) : 0) + 1;

            await this.orm.create("project.task", [{
                display_name: name,
                parent_id: this.props.record.resId,
                project_id: this.props.record.data.project_id.id,
                user_ids: this.props.record.data.user_ids.resIds,
                sequence: nextSequence,
            }]);
            this.subtaskCreate.open = false;
            this.subtaskCreate.name = "";
            this.props.record.load();
        }
    }
}

const subtaskKanbanList = {
    component: SubtaskKanbanList,
};

registry.category("view_widgets").add("subtask_kanban_list", subtaskKanbanList);
