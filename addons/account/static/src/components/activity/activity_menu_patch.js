/** @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, "account", {
    /**
     * Overridden to use "activity" view type for "account.move".
     */
    getActivityGroupViewType(model) {
        if (model === 'account.move') {
            return 'activity';
        }
        return this._super(model);
    },
});
