import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { mailModels, openView } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";

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
    action_reschedule_tomorrow(ids) {
        this.write(ids, { date_deadline: serializeDate(today().plus({ days: 1 })) });
    }
    unlink_w_meeting() {
        const eventIds = this.map((act) => act.calendar_event_id);
        const res = this.unlink(arguments[0]);
        this.env["calendar.event"].unlink(eventIds);
        return res;
    }

    get _to_store_defaults() {
        return [
            ...super._to_store_defaults,
            "res_name",
            mailDataHelpers.Store.one(
                "calendar_event_id",
                this.env["calendar.event"]._store_calendar_event_fields(...arguments)
            ),
        ];
    }
}
