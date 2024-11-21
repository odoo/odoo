import { formViewWithHtmlExpander } from "@resource/views/form_with_html_expander/form_view_with_html_expander";
import { registry } from "@web/core/registry";
import { ProjectTaskFormController } from "./project_task_form_controller";

export const projectTaskFormView = {
    ...formViewWithHtmlExpander,
    Controller: ProjectTaskFormController,
};

registry.category("views").add("project_task_form", projectTaskFormView);
