import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

const KANBAN_ON_MOBILE = ["hr.leave", "hr.leave.allocation"];

patch(ActivityMenu.prototype, {
    /**
     * Time off records carry their approve/refuse buttons far to the right of a
     * list row, which on a phone means scrolling sideways before the activity
     * can be dealt with at all. The kanban card puts them in reach.
     */
    openActivityGroup(group, filter, newWindow) {
        if (this.env.isSmall && KANBAN_ON_MOBILE.includes(group.model)) {
            group = { ...group, view_type: "kanban" };
        }
        return super.openActivityGroup(group, filter, newWindow);
    },
});
