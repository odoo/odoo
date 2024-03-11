/** @odoo-module */

import { registry } from "@web/core/registry";
import { formViewWithHtmlExpander } from '../form_with_html_expander/form_view_with_html_expander';
import { ProjectTaskFormController } from './project_task_form_controller';
import { ProjectTaskFormRenderer } from "./project_task_form_renderer";

export const projectTaskFormView = {
    ...formViewWithHtmlExpander,
    Controller: ProjectTaskFormController,
    Renderer: ProjectTaskFormRenderer,
};

registry.category("views").add("project_task_form", projectTaskFormView);
