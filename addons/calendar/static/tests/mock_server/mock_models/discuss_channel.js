import { todayMeetingDomain } from "@calendar/../tests/mock_server/mock_models/calendar_event";
import { mailModels } from "@mail/../tests/mail_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";

export class DiscussChannel extends mailModels.DiscussChannel {
    /** Meetings of the channel, the earliest first. */
    _meetings(channel) {
        const [meeting] = channel.parent_channel_id
            ? this.env["discuss.channel"].browse(channel.parent_channel_id)
            : [channel];
        return this.env["calendar.event"]
            ._filter([["videocall_channel_id", "=", meeting.id]])
            .sort((event1, event2) => event1.start.localeCompare(event2.start));
    }

    /** @override the meeting going on or coming next stands for the channel of a recurrence. */
    _meeting_dt(channel, field) {
        const events = this._meetings(channel);
        if (!events.length) {
            return super._meeting_dt(channel, field);
        }
        const now = luxon.DateTime.now();
        const event =
            events.find((event) => deserializeDateTime(event.stop) >= now) ?? events.at(-1);
        return event[field];
    }

    /** @override the channels backing a meeting of today come on top of the ad-hoc ones. */
    _get_meeting_today_ids() {
        const scheduled = this.env["calendar.event"]._filter([
            ["videocall_channel_id", "!=", false],
        ]);
        const adHocIds = super
            ._get_meeting_today_ids()
            .filter((id) => !scheduled.some((event) => event.videocall_channel_id === id));
        const todayIds = this.env["calendar.event"]
            ._filter([["videocall_channel_id", "!=", false], ...todayMeetingDomain()])
            .map((event) => event.videocall_channel_id);
        return [...todayIds, ...adHocIds];
    }

    /** @override a meeting still to come, or taking place right now, is not over. */
    _get_meeting_ongoing_ids() {
        const now = luxon.DateTime.now();
        const stillToCome = this.env["calendar.event"]
            ._filter([["videocall_channel_id", "!=", false]])
            .filter((event) => deserializeDateTime(event.stop) >= now)
            .map((event) => event.videocall_channel_id);
        return [...stillToCome, ...super._get_meeting_ongoing_ids()];
    }
}
