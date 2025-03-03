import { formViewWithHtmlExpander } from "@resource/views/form_with_html_expander/form_view_with_html_expander";
import { registry } from "@web/core/registry";
import { ProjectTaskFormController } from "./project_task_form_controller";
import { ProjectTaskKanbanQuickCreateModel } from "../project_task_kanban/project_task_kanban_quick_create_model";

export const projectTaskFormView = {
    ...formViewWithHtmlExpander,
    Controller: ProjectTaskFormController,
    Model: ProjectTaskKanbanQuickCreateModel,
};

registry.category("views").add("project_task_form", projectTaskFormView);
