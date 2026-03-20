import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    availableViews(group) {
        if (group.model === "calendar.event" && !group.is_today_meetings) {
            return [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
                [false, "activity"],
            ];
        }
        return super.availableViews(...arguments);
    },

    openActivityGroup(group, filter, newWindow) {
        if (group.is_today_meetings) {
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
