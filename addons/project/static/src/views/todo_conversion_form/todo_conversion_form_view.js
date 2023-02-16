/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { TodoConversionFormRenderer } from "./todo_conversion_form_renderer";

export const todoConversionFormView = {
    ...formView,
    Renderer: TodoConversionFormRenderer,
};

registry.category("views").add("todo_conversion_form", todoConversionFormView);
