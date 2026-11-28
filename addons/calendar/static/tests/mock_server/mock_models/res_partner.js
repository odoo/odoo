import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class ResPartner extends mailModels.ResPartner {
    upcoming_meeting_ids = fields.Many2many({
        relation: "calendar.event",
        compute: "_compute_upcoming_meeting_ids",
    });

    _compute_upcoming_meeting_ids() {
        const nowDt = DateTime.now();
        const now = serializeDateTime(nowDt);
        // Next-day start bound: only the meetings of the next 24 hours matter.
        const tomorrow = serializeDateTime(nowDt.plus({ days: 1 }));
        const eventIds = this.env["calendar.event"]
            ._filter([
                ["show_as", "=", "busy"],
                ["privacy", "not in", ["private", "confidential"]],
                ["allday", "=", false],
                ["stop", ">=", now],
                ["start", "<=", tomorrow],
            ])
            .map((event) => event.id);
        const attendees = this.env["calendar.attendee"]._filter([
            ["state", "=", "accepted"],
            ["event_id", "in", eventIds],
            ["partner_id", "in", this.map((partner) => partner.id)],
        ]);

        for (const partner of this) {
            partner.upcoming_meeting_ids = attendees
                .filter((attendee) => attendee.partner_id === partner.id)
                .map((attendee) => attendee.event_id);
        }
    }

    _store_partner_fields(res) {
        super._store_partner_fields(res);
        this._compute_upcoming_meeting_ids(); // compute not automatically triggering when necessary
        res.many("upcoming_meeting_ids", ["start", "stop"], { internal: true });
    }

    _store_avatar_card_fields(res) {
        super._store_avatar_card_fields(res);
        this._compute_upcoming_meeting_ids(); // compute not automatically triggering when necessary
        res.many("upcoming_meeting_ids", ["start", "stop"], { internal: true });
    }
}
