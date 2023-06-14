/** @odoo-module */

import { ActivityService, insertActivity } from "@mail/core/web/activity_service";
import { patchFn } from "@mail/utils/common/patch";
import { patch } from "@web/core/utils/patch";

let actionService;
let orm;

patchFn(insertActivity, function (data) {
    const activity = this._super(...arguments);
    const { calendar_event_id: calendarEventId } = data;
    if (calendarEventId) {
        activity["calendar_event_id"] = calendarEventId;
    }
    return activity;
});

export async function rescheduleMeeting(activityId) {
    const action = await orm.call("mail.activity", "action_create_calendar_event", [[activityId]]);
    actionService.doAction(action);
}

patch(ActivityService.prototype, "calendar/activity_service", {
    setup(env, services) {
        this._super(...arguments);
        actionService = services.action;
        orm = services.orm;
    },
});
