import { Activity } from "@mail/core/common/activity_model";
import { fields, patchModel } from "@mail/model/export";

export const activityPatch = patchModel(Activity, {
    setup() {
        super.setup();
        this.calendar_event_id = fields.One("calendar.event");
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
