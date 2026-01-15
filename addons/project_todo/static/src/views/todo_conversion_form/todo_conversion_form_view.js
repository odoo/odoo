import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { TodoConversionFormController } from "./todo_conversion_form_controller";

export const todoConversionFormView = {
    ...formView,
    Controller: TodoConversionFormController,
};

registry.category("views").add("todo_conversion_form", todoConversionFormView);
