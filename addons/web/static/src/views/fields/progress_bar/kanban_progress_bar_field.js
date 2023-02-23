/** @odoo-module **/

import { registry } from "@web/core/registry";
import { progressBarField, ProgressBarField } from "./progress_bar_field";

export class KanbanProgressBarField extends ProgressBarField {
    onClick() {
        if (this.props.isEditable) {
            this.state.isEditing = true;
        }
    }
}

export const kanbanProgressBarField = {
    ...progressBarField,
    component: KanbanProgressBarField,
};

registry.category("fields").add("kanban.progressbar", kanbanProgressBarField);
