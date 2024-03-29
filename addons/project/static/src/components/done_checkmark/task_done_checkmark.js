import { useState, onRendered } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BooleanToggleField, booleanToggleField } from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class TaskCheckMark extends BooleanToggleField {
    static template = "project.TaskCheckMark";

    setup() {
        super.setup();
        this.reached = useState({
            isReached: false,
            notReloadState: false,
        });
        onRendered(() => {
            if (!this.reached.notReloadState) {
                this.reached.isReached = this.props.record.data[this.props.name];
            }
        });
    }

    async onChange(ev) {
        const value = !this.props.record.data[this.props.name];
        if (['kanban', 'list'].includes(this.props.viewType)) {
            await this.props.record.update(value, { save: this.props.autosave });
        } else {
            await this.props.record.update({ [this.props.name]: value });
        }
    }
}

export const taskCheckMark = {
    ...booleanToggleField,
    component: TaskCheckMark,
}

registry.category("fields").add("task_done_checkmark", taskCheckMark);
