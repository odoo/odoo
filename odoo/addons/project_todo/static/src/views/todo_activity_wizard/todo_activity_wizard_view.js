/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { TodoActivityWizardController } from "./todo_activity_wizard_controller";

export const todoActivityWizardView = {
    ...formView,
    Controller: TodoActivityWizardController,
};

registry.category("views").add("todo_activity_wizard", todoActivityWizardView);
