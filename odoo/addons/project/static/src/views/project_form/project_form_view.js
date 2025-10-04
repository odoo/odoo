/** @odoo-module */

import { registry } from "@web/core/registry";
import { formViewWithHtmlExpander } from '../form_with_html_expander/form_view_with_html_expander';
import { ProjectFormRenderer } from "./project_form_renderer";

export const projectFormView = {
    ...formViewWithHtmlExpander,
    Renderer: ProjectFormRenderer,
};

registry.category("views").add("project_form", projectFormView);
