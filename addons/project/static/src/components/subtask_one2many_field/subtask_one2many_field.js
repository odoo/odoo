/** @odoo-module */

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

import { SubtaskListRenderer } from './subtask_list_renderer';

export class SubtaskOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SubtaskListRenderer,
    };

    get rendererProps() {
        const rendererProps = super.rendererProps;
        if (this.props.viewMode === "kanban") {
            rendererProps.openRecord = this.switchToForm.bind(this);
        }
        return rendererProps;
    }
}

export const subtaskOne2ManyField = {
    ...x2ManyField,
    component: SubtaskOne2ManyField,
    additionalClasses: ["o_field_one2many"],
}

registry.category("fields").add("subtasks_one2many", subtaskOne2ManyField);
