/** @odoo-module **/

import { registry } from "@web/core/registry";
import { activityView } from "@mail/views/web/activity/activity_view";
import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";

export const projectActivityView = {
    ...activityView,
    ControlPanel: ProjectControlPanel,
};
registry.category("views").add("project_activity", projectActivityView);
