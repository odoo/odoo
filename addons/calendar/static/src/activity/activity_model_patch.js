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
    async rescheduleMeeting() {
        const action = await this.store.env.services.orm.call(
            "mail.activity",
            "action_create_calendar_event",
            [[this.id]]
        );
        this.store.env.services.action.doAction(action);
    },
});
