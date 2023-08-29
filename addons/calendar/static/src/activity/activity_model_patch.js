/** @odoo-module */

import { Activity } from "@mail/core/web/activity_model";
import { patch } from "@web/core/utils/patch";

patch(Activity, {
    insert(data) {
        const activity = super.insert(...arguments);
        const { calendar_event_id: calendarEventId } = data;
        if (calendarEventId) {
            activity["calendar_event_id"] = calendarEventId;
        }
        return activity;
    },
});
