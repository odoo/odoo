import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/export";

import { toLocaleDateTimeString } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    setup() {
        super.setup(...arguments);
        this.upcoming_meeting_ids = fields.Many("calendar.event");
        this.inMeetingEndText = this.computedUntilStale(
            () => {
                const now = DateTime.now();
                let meetingUntil = now;
                const meetings = this.upcoming_meeting_ids.toSorted(
                    (a, b) => a.start - b.start || a.id - b.id
                );
                for (const meeting of meetings) {
                    if (meeting.start > meetingUntil) {
                        break; // gap after the running meetings
                    }
                    meetingUntil = DateTime.max(meetingUntil, meeting.stop);
                }
                if (this.isBot || meetingUntil <= now) {
                    return "";
                }
                const time = meetingUntil.hasSame(this.store.startOfToday, "day")
                    ? meetingUntil.toLocaleString(DateTime.TIME_SIMPLE)
                    : toLocaleDateTimeString(meetingUntil);
                return _t("In a meeting until %(time)s", { time });
            },
            // stale when a meeting starts or ends
            () =>
                DateTime.min(
                    ...this.upcoming_meeting_ids
                        .flatMap((meeting) => [meeting.start, meeting.stop])
                        .filter((dt) => dt > DateTime.now())
                )
                    ?.diffNow()
                    .toMillis()
        );
    },

    statusSubtitleParts() {
        const parts = super.statusSubtitleParts();
        if (!this.inMeetingEndText) {
            return parts;
        }
        return [
            { class: "text-success fw-bold opacity-75", text: this.inMeetingEndText },
            ...parts,
        ];
    },
};
patch(ResPartner.prototype, resPartnerPatch);
