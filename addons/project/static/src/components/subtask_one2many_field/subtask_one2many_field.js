/** @odoo-module */

import { registry } from "@web/core/registry";
import { X2ManyField } from '@web/views/fields/x2many/x2many_field';

import { SubtaskListRenderer } from './subtask_list_renderer';

export class SubtaskOne2ManyField extends X2ManyField {
    get Renderer() {
        return this.viewMode === 'list' ? SubtaskListRenderer : super.Renderer;
    }
}

SubtaskOne2ManyField.components = {
    ...X2ManyField,
    ListRenderer: SubtaskListRenderer,
}

registry.category("fields").add("subtasks_one2many", SubtaskOne2ManyField);
