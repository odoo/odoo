/** @odoo-module */

import { registry } from "@web/core/registry";
import { formViewWithHtmlExpander } from '../form_with_html_expander/form_view_with_html_expander';
import { ProjectTaskFormRenderer } from "./project_task_form_renderer";

export const projectTaskFormView = {
    ...formViewWithHtmlExpander,
    Renderer: ProjectTaskFormRenderer,
};

registry.category("views").add("project_task_form", projectTaskFormView);
