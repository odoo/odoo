import { mailModels, openView } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class MailActivity extends mailModels.MailActivity {
    name = fields.Char();

    async action_create_calendar_event() {
        await openView({
            res_model: "calendar.event",
            views: [[false, "calendar"]],
        });
        return {
            type: "ir.actions.act_window",
            name: "Meetings",
            res_model: "calendar.event",
            view_mode: "calendar",
            views: [[false, "calendar"]],
            target: "current",
        };
    }
    unlink_w_meeting() {
        const eventIds = this.map((act) => act.calendar_event_id);
        const res = this.unlink(arguments[0]);
        this.env["calendar.event"].unlink(eventIds);
        return res;
    }

    /** @param {number[]} ids */
    _to_store(store) {
        super._to_store(...arguments);
        for (const activity of this) {
            if (activity.calendar_event_id) {
                store._add_record_fields(this.browse(activity.id), {
                    calendar_event_id: activity.calendar_event_id,
                });
            }
        }
    }
}
