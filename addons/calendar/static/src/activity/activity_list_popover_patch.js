import { ActivityListPopover } from "@mail/core/web/activity_list_popover";
import { patch } from "@web/core/utils/patch";

patch(ActivityListPopover.prototype, {
    get overdueActivities() {
        return this.activities.filter(
            (activity) => activity.state === "overdue" && activity.activityStatus === "overdue"
        );
    },

    get todayActivities() {
        return this.activities.filter(
            (activity) => activity.state === "today" || activity.activityStatus === "ongoing"
        );
    },
});
