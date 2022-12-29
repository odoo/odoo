/** @odoo-module */

import { ActivityService } from "@mail/new/web/activity/activity_service";
import { patch } from "@web/core/utils/patch";

patch(ActivityService.prototype, "calendar/activity_service", {
    insert(data) {
        const activity = this._super(data);
        const { calendar_event_id: calendarEventId } = data;
        if (calendarEventId) {
            activity["calendar_event_id"] = calendarEventId;
        }
        return activity;
    },

    async rescheduleMeeting(activityId) {
        const action = await this.orm.call("mail.activity", "action_create_calendar_event", [
            [activityId],
        ]);
        this.env.services.action.doAction(action);
    },
});
