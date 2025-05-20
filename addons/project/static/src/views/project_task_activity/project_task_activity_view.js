import { activityView } from "@mail/views/web/activity/activity_view";

import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";
import { ProjectTaskActivityModel } from "./project_task_activity_model";
import { registry } from "@web/core/registry";

export const projectTaskActivityView = {
    ...activityView,
    ControlPanel: ProjectTaskControlPanel,
    Model: ProjectTaskActivityModel,
}

registry.category("views").add("project_task_activity", projectTaskActivityView);
