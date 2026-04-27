import { registry } from "@web/core/registry";
import { projectTaskGraphView } from "@project/views/project_task_graph/project_task_graph_view";
import { HighlightProjectTaskSearchModel } from "../highlight_project_task_search_model";

registry.category("views").add("project_enterprise_task_graph", {
    ...projectTaskGraphView,
    SearchModel: HighlightProjectTaskSearchModel,
});
