import { registry } from "@web/core/registry";
import { activityView } from "@mail/views/web/activity/activity_view";
import { HighlightProjectTaskSearchModel } from "../highlight_project_task_search_model";

registry.category("views").add("project_enterprise_activity", {
    ...activityView,
    SearchModel: HighlightProjectTaskSearchModel,
});
