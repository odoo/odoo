import { formViewWithHtmlExpander } from "@resource/views/form_with_html_expander/form_view_with_html_expander";
import { registry } from "@web/core/registry";
import { ProjectProjectFormController } from "./project_project_form_controller";

export const projectProjectFormView = {
    ...formViewWithHtmlExpander,
    Controller: ProjectProjectFormController,
};

registry.category("views").add("project_project_form", projectProjectFormView);
