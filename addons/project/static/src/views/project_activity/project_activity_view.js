/** @odoo-module **/

import { registry } from "@web/core/registry";
import { activityView } from "@mail/views/web/activity/activity_view";

export const projectActivityView = {
    ...activityView,
};
registry.category("views").add("project_activity", projectActivityView);
