import { registry } from "@web/core/registry";
import { projectTaskKanbanView } from "@project/views/project_task_kanban/project_task_kanban_view";
import { HighlightProjectTaskSearchModel } from "../highlight_project_task_search_model";

registry.category("views").add("project_enterprise_task_kanban", {
    ...projectTaskKanbanView,
    SearchModel: HighlightProjectTaskSearchModel,
});
