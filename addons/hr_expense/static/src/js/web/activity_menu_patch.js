import { ActivityMenu } from "@mail/core/web/activity_menu";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    openActivityGroup(group) {
        if (group.model === "hr.expense") {
            const mobileMaxWidth = MEDIAS_BREAKPOINTS[SIZES.MD].minWidth;
            const onMobile = window.innerWidth <= mobileMaxWidth;

            if (onMobile) {
                group.view_type = "kanban";
            }
        }
        return super.openActivityGroup(...arguments);
    },
});
