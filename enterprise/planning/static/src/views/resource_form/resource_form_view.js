/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { ResourceFormController } from "@planning/views/resource_form/resource_form_controller";

export const ResourceFormView = {
    ...formView,
    Controller: ResourceFormController,
};

registry.category("views").add("resource_form_view", ResourceFormView);
