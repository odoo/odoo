/** @odoo-module */

import { ActivityService } from "@mail/core/web/activity_service";
import { patch } from "@web/core/utils/patch";

patch(ActivityService.prototype, {
    async rescheduleMeeting(activityId) {
        const action = await this.orm.call("mail.activity", "action_create_calendar_event", [
            [activityId],
        ]);
        this.env.services.action.doAction(action);
    },
});
