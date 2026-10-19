import { ActivityMenu } from "@mail/core/web/activity_menu";

import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    /**
     * Show the sub-task when clicking on the task activities menu.
     */
    async executeActivityAction(group, domain, views, context, newWindow) {
        if (group.model === "project.task") {
            context.activity_action = true;
        }
        return super.executeActivityAction(...arguments);
    },
});
