import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    openActivityGroup(group, filter, newWindow) {
        if (this.env.isSmall && ["hr.leave", "hr.leave.allocation"].includes(group.model)) {
            group = { ...group, view_type: "kanban" };
        }
        return super.openActivityGroup(group, filter, newWindow);
    },
});
