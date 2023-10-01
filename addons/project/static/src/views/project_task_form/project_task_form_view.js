/** @odoo-module */

import { registry } from "@web/core/registry";
import { ProjectTaskFormController } from "./project_task_form_controller";
import { formView } from '@web/views/form/form_view';

export const projectTaskFormView = {
    ...formView,
    Controller: ProjectTaskFormController,
};

registry.category("views").add("project_task_form", projectTaskFormView);
