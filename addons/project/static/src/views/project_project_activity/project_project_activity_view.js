import { activityView } from "@mail/views/web/activity/activity_view";

import { ProjectActivityModel } from "./project_project_activity_model";
import { registry } from "@web/core/registry";

export const projectProjectActivityView = {
    ...activityView,
    Model: ProjectActivityModel,
}

registry.category("views").add("project_project_activity", projectProjectActivityView);
