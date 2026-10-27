/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { TodoFormControlPanel } from "./todo_form_control_panel";
import { TodoFormController } from "./todo_form_controller";
import { TodoFormRenderer } from "./todo_form_renderer";

export const todoFormView = {
    ...formView,
    ControlPanel: TodoFormControlPanel,
    Controller: TodoFormController,
    Renderer: TodoFormRenderer,
};

registry.category("views").add("todo_form", todoFormView);
