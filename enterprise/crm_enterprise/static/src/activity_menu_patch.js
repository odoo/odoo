/* @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

import "@crm/activity_menu_patch";

patch(ActivityMenu.prototype, {
    availableViews(group) {
        if (group.model === "crm.lead") {
            return [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
                [false, "calendar"],
                [false, "pivot"],
                [false, "cohort"],
                [false, "map"],
                [false, "activity"],
            ];
        }
        return super.availableViews(...arguments);
    },
});
