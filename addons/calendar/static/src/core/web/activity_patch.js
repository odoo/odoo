import { Activity } from "@mail/core/web/activity";
import { formatList } from "@web/core/l10n/utils";
import { isToday } from "@mail/utils/common/dates";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(Activity.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.isToday = isToday;
    },
    get attendeeNames() {
        if (!this.meeting || !this.meeting.partner_ids) {
            return false;
        }
        return formatList(this.meeting.partner_ids.map((p) => p.name));
    },
    get dateFormat() {
        return luxon.DateTime.DATE_FULL;
    },
    get meeting() {
        return this.props.activity.calendar_event_id;
    },
    get timeFormat() {
        return luxon.DateTime.TIME_SIMPLE;
    },
    get truncatedAttendeeNames() {
        return this.meeting.partner_ids.length > 3
            ? formatList([
                ...this.meeting.partner_ids.slice(0, 2).map((p) => p.name),
                _t("%s others", this.meeting.partner_ids.length - 2),
            ])
            : this.attendeeNames;
    },
    async onClickReschedule() {
        await this.props.activity.rescheduleMeeting();
    },
});
