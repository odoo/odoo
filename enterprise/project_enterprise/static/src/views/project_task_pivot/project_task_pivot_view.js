import { registry } from "@web/core/registry";
import { projectPivotView } from "@project/views/project_task_pivot/project_pivot_view";
import { HighlightProjectTaskSearchModel } from "../highlight_project_task_search_model";

registry.category("views").add("project_enterprise_task_pivot", {
    ...projectPivotView,
    SearchModel: HighlightProjectTaskSearchModel,
});
