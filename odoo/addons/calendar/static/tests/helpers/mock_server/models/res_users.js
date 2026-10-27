/** @odoo-module **/

// ensure mail override is applied first.
import "@mail/../tests/helpers/mock_server/models/res_users";

import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";
import { MockServer } from "@web/../tests/helpers/mock_server";
const { DateTime } = luxon;

patch(MockServer.prototype, {
    /**
     * Simulates `_systray_get_calendar_event_domain` on `res.users`.
     *
     * @private
     */
    _mockResUsers_SystrayGetCalendarEventDomain() {
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

        const currentPartnerAttendeeIds = this.pyEnv["calendar.attendee"].search([
            ["partner_id", "=", this.pyEnv.currentPartnerId],
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
            "&",
            ["allday", "=", true],
            ["start_date", "=", serializeDateTime(startDate)],
            ["attendee_ids", "in", currentPartnerAttendeeIds],
        ];
    },

    /**
     * Simulates `systray_get_activities` on `res.users`.
     *
     * @override
     */
    _mockResUsersSystrayGetActivities() {
        const activities = super._mockResUsersSystrayGetActivities(...arguments);
        const meetingsLines = this.pyEnv["calendar.event"].searchRead(
            this._mockResUsers_SystrayGetCalendarEventDomain(),
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
    },
});
