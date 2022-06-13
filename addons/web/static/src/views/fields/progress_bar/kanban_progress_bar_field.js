/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ProgressBarField } from "./progress_bar_field";

export class KanbanProgressBarField extends ProgressBarField {
    onClick() {
        if (this.props.isEditable && !this.props.record.isReadonly(this.props.name)) {
            this.state.isEditing = true;
        }
    }
}

registry.category("fields").add("kanban.progressbar", KanbanProgressBarField);
