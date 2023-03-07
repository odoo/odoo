/** @odoo-module **/

import { registry } from "@web/core/registry";
import { todoFormView } from "@note/views/todo_form/todo_form_view";
import { TodoFormControllerWithConversion } from "./todo_form_controller";

export const todoFormViewWithConversion = {
    ...todoFormView,
    Controller: TodoFormControllerWithConversion,
    props: (genericProps, view) => {
        const viewProps = todoFormView.props(genericProps,view);
        viewProps.info.actionMenus.action = [];
        viewProps.info.actionMenus.print = [];
        return viewProps;
    },
};

registry.category("views").add("todo_form_with_conversion", todoFormViewWithConversion);
