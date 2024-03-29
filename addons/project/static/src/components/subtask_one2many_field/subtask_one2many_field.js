/** @odoo-module */

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

import { SubtaskListRenderer } from './subtask_list_renderer';

export class SubtaskOne2ManyField extends X2ManyField {}

SubtaskOne2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: SubtaskListRenderer,
}

export const subtaskOne2ManyField = {
    ...x2ManyField,
    component: SubtaskOne2ManyField,
}

registry.category("fields").add("subtasks_one2many", subtaskOne2ManyField);
