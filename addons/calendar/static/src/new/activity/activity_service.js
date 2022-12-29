/** @odoo-module */

import { ActivityService } from "@mail/new/activity/activity_service";
import { patch } from "@web/core/utils/patch";

patch(ActivityService.prototype, "calendar/activity_service", {
    update(activity, data) {
        this._super(activity, data);
        const { calendar_event_id: calendarEventId } = data;
        if (calendarEventId) {
            activity["calendar_event_id"] = calendarEventId;
        }
    },
});
