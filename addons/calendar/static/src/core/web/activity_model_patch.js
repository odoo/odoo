import { Activity } from "@mail/core/common/activity_model";
import { fields } from "@mail/model/export";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup();
        this.calendar_event_id = fields.One("calendar.event");
    },
});

/** @type {import("models").Activity} */
const activityPatch = {
    async rescheduleMeeting() {
        const action = await this.store.env.services.orm.call(
            "mail.activity",
            "action_create_calendar_event",
            [[this.id]]
        );
        this.store.env.services.action.doAction(action);
    },
};
patch(Activity.prototype, activityPatch);
