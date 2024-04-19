import { Activity } from "@mail/core/web/activity_model";
import { assignIn } from "@mail/utils/common/misc";
import { computeDelay } from "@mail/utils/common/dates";
import { patch } from "@web/core/utils/patch";
import { Record } from "@mail/core/common/record";

patch(Activity, {
    _insert(data) {
        const activity = super._insert(...arguments);
        assignIn(activity, data, ["calendar_event_id"]);
        return activity;
    },
});

/** @type {import("models").Activity} */
const activityPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {luxon.DateTime} */
        this.start = Record.attr(undefined, { type: "datetime" });
        /** @type {luxon.DateTime} */
        this.stop = Record.attr(undefined, { type: "datetime" });
    },

    get activityTime() {
        if (this.start && this.stop) {
            const startTime = this.start.toLocaleString(luxon.DateTime.TIME_24_SIMPLE);
            const stopTime = this.stop.toLocaleString(luxon.DateTime.TIME_24_SIMPLE);
            if (this.start.toISODate() === this.stop.toISODate()) {
                return `(${startTime} - ${stopTime})`;
            }
            const diff = computeDelay(this.date_deadline);
            const startDate = this.start.toLocaleString({ month: "short", day: "numeric" });
            const stopDate = this.stop.toLocaleString({ month: "short", day: "numeric" });
            return [-1, 0, 1].includes(diff)
                ? `(${startTime}) - ${stopDate} (${stopTime})`
                : `${startDate} (${startTime}) - ${stopDate} (${stopTime})`;
        }
        return false;
    },

    get isLongActivity() {
        if (this.start && this.stop) {
            return !this.start.hasSame(this.stop, "day");
        }
        return false;
    },

    get activityStatus() {
        const now = luxon.DateTime.now();
        if (this.start && this.stop) {
            if (this.start <= now && now <= this.stop) {
                return "ongoing";
            } else if (this.stop < now) {
                return "overdue";
            }
        } else {
            if (this.state === "today") {
                return "ongoing";
            } else if (this.state === "overdue") {
                return "overdue";
            }
        }
        return "not_started";
    },

    async rescheduleMeeting() {
        const action = await this.store.env.services.orm.call(
            "mail.activity",
            "action_create_calendar_event",
            [[this.id]]
        );
        this.store.env.services.action.doAction(action);
    },
};
patch(Activity.prototype, activityPatch);
