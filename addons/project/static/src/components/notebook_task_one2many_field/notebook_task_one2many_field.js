/** @odoo-module */

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

import { NotebookTaskListRenderer } from './notebook_task_list_renderer';

export class NotebookTaskOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: NotebookTaskListRenderer,
    };
}

export const notebookTaskOne2ManyField = {
    ...x2ManyField,
    component: NotebookTaskOne2ManyField,
}

registry.category("fields").add("notebook_task_one2many", notebookTaskOne2ManyField);
