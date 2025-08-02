/** @odoo-module */

import { Activity } from "@mail/core/web/activity_model";
import { assignIn } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(Activity, {
    _insert(data) {
        const activity = super._insert(...arguments);
        assignIn(activity, data, ["calendar_event_id"]);
        return activity;
    },
});
