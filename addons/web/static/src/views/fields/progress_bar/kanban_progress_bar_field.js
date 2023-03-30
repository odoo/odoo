/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ProgressBarField } from "./progress_bar_field";

export class KanbanProgressBarField extends ProgressBarField {
    get isEditable() {
        return this.props.isEditable;
    }
}

registry.category("fields").add("kanban.progressbar", KanbanProgressBarField);
