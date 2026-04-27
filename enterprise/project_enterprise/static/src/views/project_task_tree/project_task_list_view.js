import { projectTaskListView } from "@project/views/project_task_list/project_task_list_view";
import { registry } from "@web/core/registry";
import { HighlightProjectTaskSearchModel } from "../highlight_project_task_search_model";

export const projectEnterpriseTaskListView = {
    ...projectTaskListView,
    SearchModel: HighlightProjectTaskSearchModel,
};
registry.category("views").add("project_enterprise_task_list", projectEnterpriseTaskListView);
