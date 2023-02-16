/** @odoo-module **/

import { registry } from "@web/core/registry";
import { todoFormView } from "@note/views/project_task_form/todo_form_view";
import { TodoFormControllerWithConversion } from "./todo_form_controller";

export const todoFormViewWithConversion = {
    ...todoFormView,
    Controller: TodoFormControllerWithConversion,
};

registry.category("views").add("todo_form_with_conversion", todoFormViewWithConversion);
