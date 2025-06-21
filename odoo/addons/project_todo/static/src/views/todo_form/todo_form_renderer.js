/* @odoo-module */

import { FormRenderer } from "@web/views/form/form_renderer";

import { TodoFormStatusBarButtons } from "./todo_form_status_bar_button";

export class TodoFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        StatusBarButtons: TodoFormStatusBarButtons,
    };
}
