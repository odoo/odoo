/* @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {

    openActivityGroup(group, filter = "all") {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_ActivityMenuView_activityGroup).
        const context = {};
        if (group.model !== "project.task") {
            return super.openActivityGroup(...arguments);
        }
        document.body.click();
        if (filter === "all") {
            context["search_default_activities_overdue"] = 1;
            context["search_default_activities_today"] = 1;
        } else {
            context["search_default_activities_" + filter] = 1;
        }
        this.action.doAction("project.action_view_task_from_systray", {
            additionalContext: context,
            clearBreadcrumbs: true,
        });
    },
});
