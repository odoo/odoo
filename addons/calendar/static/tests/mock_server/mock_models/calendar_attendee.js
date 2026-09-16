import { fields, models } from "@web/../tests/web_test_helpers";

export class CalendarAttendee extends models.ServerModel {
    _name = "calendar.attendee";

    event_id = fields.Many2one({ relation: "calendar.event" });
    partner_id = fields.Many2one({ relation: "res.partner" });
    state = fields.Selection({
        selection: [
            ["accepted", "Yes"],
            ["declined", "No"],
            ["tentative", "Maybe"],
            ["needsAction", "Needs Action"],
        ],
        default: "needsAction",
    });
}
