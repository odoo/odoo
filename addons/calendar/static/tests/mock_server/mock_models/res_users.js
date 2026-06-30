import { mailModels } from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

export class ResUsers extends mailModels.ResUsers {
    /**
     * Simulates `_systray_get_calendar_event_domain` on `res.users`.
     *
     * @private
     */
    _systray_get_calendar_event_domain() {
        const startDate = DateTime.fromObject({
            hours: 0,
            minutes: 0,
            seconds: 0,
            milliseconds: 0,
        });
        const endDate = DateTime.fromObject({
            hours: 23,
            minutes: 59,
            seconds: 59,
            milliseconds: 999,
        });

        const currentPartnerAttendeeIds = this.env["calendar.attendee"].search([
            ["partner_id", "=", serverState.partnerId],
            ["state", "!=", "declined"],
        ]);
        return [
            "&",
            "|",
            "&",
            "|",
            ["start", ">=", serializeDateTime(startDate)],
            ["stop", ">=", serializeDateTime(startDate)],
            ["start", "<=", serializeDateTime(endDate)],
            // FIXME: Makes "activity_menu.test.js" fail
            // "&",
            // ["allday", "=", true],
            // ["start_date", "=", serializeDateTime(startDate)],
            ["attendee_ids", "in", [...currentPartnerAttendeeIds]],
        ];
    }

    /** @override */
    _get_activity_groups() {
        const activities = super._get_activity_groups();
        const meetingsLines = this.env["calendar.event"].search_read(
            this._systray_get_calendar_event_domain(),
            {
                fields: ["id", "start", "name", "allday"],
                order: "start",
            }
        );
        if (meetingsLines.length) {
            activities.unshift({
                id: "calendar.event", // for simplicity
                meetings: meetingsLines,
                model: "calendar.event",
                name: "Today's Meetings",
                type: "meeting",
            });
        }
        return activities;
    }
}
