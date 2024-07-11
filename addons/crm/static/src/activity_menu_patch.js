/* @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    availableViews(group) {
        if (group.model === "crm.lead") {
            return [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
                [false, "calendar"],
                [false, "pivot"],
                [false, "graph"],
                [false, "activity"],
            ];
        }
        return super.availableViews(...arguments);
    },

    openActivityGroup(group, filter = "all") {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_ActivityMenuView_activityGroup).
        const context = {};
        if (group.model === "crm.lead") {
            document.body.click(); // hack to close dropdown
            if (filter === "my") {
                context["search_default_activities_overdue"] = 1;
                context["search_default_activities_today"] = 1;
            } else {
                context["search_default_activities_" + filter] = 1;
            }
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            context["force_search_count"] = 1;
            this.action.doAction("crm.crm_lead_action_my_activities", {
                additionalContext: context,
                clearBreadcrumbs: true,
            });
        } else {
            return super.openActivityGroup(group, filter);
        }
    },
});
