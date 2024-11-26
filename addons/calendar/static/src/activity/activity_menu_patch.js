import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    openActivityGroup(group, filter, newWindow) {
        if (group.model === "calendar.event") {
            this.dropdown.close();
            this.action.doAction("calendar.action_calendar_event", {
                newWindow,
                additionalContext: {
                    default_mode: "day",
                    search_default_mymeetings: 1,
                },
                clearBreadcrumbs: true,
            });
        } else {
            super.openActivityGroup(...arguments);
        }
    },
});
