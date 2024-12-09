import { formViewWithHtmlExpander } from "@resource/views/form_with_html_expander/form_view_with_html_expander";

import { registry } from "@web/core/registry";

import { ProjectUpdateFormModel } from "./project_update_form_model";

export const projectUpdateFormView = {
    ...formViewWithHtmlExpander,
    Model: ProjectUpdateFormModel,
};

registry.category("views").add("project_update_form", projectUpdateFormView);
