import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class ResPartner extends mailModels.ResPartner {
    meeting_until = fields.Datetime({ compute: "_compute_meeting_until" });

    _compute_meeting_until() {
        const now = serializeDateTime(DateTime.now());
        for (const partner of this) {
            partner.meeting_until = false;
        }

        const eventIds = this.env["calendar.event"]
            ._filter([
                ["show_as", "=", "busy"],
                ["privacy", "not in", ["private", "confidential"]],
                ["allday", "=", false],
                ["stop", ">=", now],
            ])
            .map((event) => event.id);
        const attendees = this.env["calendar.attendee"]._filter([
            ["state", "=", "accepted"],
            ["event_id", "in", eventIds],
            ["partner_id", "in", this.map((partner) => partner.id)],
        ]);

        const attendeesByPartnerId = {};
        for (const attendee of attendees) {
            (attendeesByPartnerId[attendee.partner_id] ||= []).push(attendee);
        }
        for (const partner of this) {
            const partnerAttendees = attendeesByPartnerId[partner.id];
            if (!partnerAttendees) {
                continue;
            }
            const events = [
                ...this.env["calendar.event"].browse(
                    partnerAttendees.map((attendee) => attendee.event_id)
                ),
            ].sort((a, b) => (a.start < b.start ? -1 : 1));
            let meetingUntil = now;
            for (const event of events) {
                if (event.start > meetingUntil) {
                    break;
                }
                meetingUntil = event.stop > meetingUntil ? event.stop : meetingUntil;
            }
            if (meetingUntil > now) {
                partner.meeting_until = meetingUntil;
            }
        }
    }

    _store_partner_fields(res) {
        super._store_partner_fields(res);
        this._compute_meeting_until(); // compute not automatically triggering when necessary
        res.attr("meeting_until", undefined, {
            predicate: (partner) => partner.meeting_until,
            internal: true,
        });
    }
}
