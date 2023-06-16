/** @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    /**
     * Overridden to use "activity" view type for "project.project" and "project.task".
     */
    getActivityGroupViewType(model) {
        if (['project.project', 'project.task'].includes(model)) {
            return 'activity';
        }
        return super.getActivityGroupViewType(...arguments);
    },
});
