import { Component, proxy, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { Field, getPropertyFieldInfo } from "@web/views/fields/field";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { SubtaskCreate } from "./subtask_kanban_create/subtask_kanban_create";
import { isClosedState } from "../../utils/project_utils";

export class SubtaskKanbanList extends Component {
    static components = {
        Field,
        SubtaskCreate,
    };
    props = useProps(standardWidgetProps);
    static template = "project.SubtaskKanbanList";

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.isClosedState = isClosedState;
        this.subtaskCreate = proxy({
            open: false,
        });
        // Sub-tasks list (child_ids) from which `openSubtaskIdsAtLoad` was computed.
        this.subtasksAtLoad = null;
        // Ids of the sub-tasks that were open when the parent task was last loaded.
        this.openSubtaskIdsAtLoad = new Set();
    }

    get subtasks() {
        return this.props.record.data.child_ids;
    }

    /**
     * Sub-tasks to display: those that were open when the parent task was last
     * loaded. A sub-task closed from the card stays visible (greyed out) until
     * the next load, so the row does not vanish under the user's cursor.
     * Each load of the parent creates a new child_ids list, which is what
     * triggers a new snapshot of the open ids.
     */
    get displayedSubtasks() {
        if (this.subtasksAtLoad !== this.subtasks) {
            this.subtasksAtLoad = this.subtasks;
            this.openSubtaskIdsAtLoad = new Set(
                this.subtasks.records
                    .filter((subtask) => !this.isClosedState(subtask.data.state))
                    .map((subtask) => subtask.resId)
            );
        }
        return this.subtasks.records.filter((subtask) => this.openSubtaskIdsAtLoad.has(subtask.resId));
    }

    get fieldInfo() {
        return {
            state: {
                ...getPropertyFieldInfo({
                    name: "state",
                    type: "selection",
                    widget: "project_task_state_selection",
                }),
                viewType: "card",
            },
        };
    }

    async goToSubtask(subtask_id) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.subtasks.resModel,
            res_id: subtask_id,
            views: [[false, "form"]],
            target: "current",
            context: {
                active_id: subtask_id,
            },
        });
    }

    onAddSubtaskClick() {
        this.subtaskCreate.open = true;
    }

    onSubtaskCreateClose() {
        this.subtaskCreate.open = false;
    }

    async _onSubtaskCreateNameChanged(name) {
        if (name.trim() === "") {
            this.notification.add(_t("Invalid Display Name"), {
                type: "danger",
            });
        } else {
            const sequences = this.subtasks.records.map(r => r.data.sequence);
            const nextSequence = (sequences.length ? Math.max(...sequences) : 0) + 1;

            await this.orm.create("project.task", [{
                display_name: name,
                parent_id: this.props.record.resId,
                project_id: this.props.record.data.project_id.id,
                user_ids: this.props.record.data.user_ids.resIds,
                sequence: nextSequence,
            }]);
            this.subtaskCreate.open = false;
            this.props.record.load();
        }
    }
}

const subtaskKanbanList = {
    component: SubtaskKanbanList,
};

registry.category("view_widgets").add("subtask_kanban_list", subtaskKanbanList);
