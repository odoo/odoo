import { ResUsers } from "@mail/core/common/res_users_model";
import { patch } from "@web/core/utils/patch";

patch(ResUsers.prototype, {
    get meetingStatus() {
        if (!this.in_meeting_until) {
            return null;
        }
        const untilDate = luxon.DateTime.fromSQL(this.in_meeting_until, { zone: "utc" });
        if (untilDate > luxon.DateTime.now()) {
            return untilDate.toLocal().toLocaleString(luxon.DateTime.TIME_SIMPLE);
        }
        return null;
    },
});
