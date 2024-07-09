/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { TodoFormController } from "./todo_form_controller";
import { TodoFormControlPanel } from "./todo_form_control_panel";

export const todoFormView = {
    ...formView,
    Controller: TodoFormController,
    ControlPanel: TodoFormControlPanel,
};

registry.category("views").add("todo_form", todoFormView);
