import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { patch } from "@web/core/utils/patch";
import { computeDelay } from "@mail/utils/common/dates";
import { _t } from "@web/core/l10n/translation";

patch(ActivityListPopoverItem.prototype, {
    get hasEditButton() {
        return super.hasEditButton && !this.props.activity.calendar_event_id;
    },

    async onClickReschedule() {
        await this.props.activity.rescheduleMeeting();
    },
    get delayLabel() {
        const diff = computeDelay(this.props.activity.date_deadline);
        const activityTime = this.props.activity.activityTime || "";
        if (diff === 0) {
            return _t("Today %s", activityTime);
        } else if (diff === -1) {
            return this.props.activity.activityStatus === "ongoing"
                ? _t("Yesterday %s", activityTime)
                : _t("Yesterday");
        } else if (diff < 0) {
            return this.props.activity.activityStatus === "ongoing"
                ? activityTime
                : _t("%s days overdue", Math.round(Math.abs(diff)));
        } else if (diff === 1) {
            return _t("Tomorrow %s", activityTime);
        } else {
            return this.props.activity.isLongActivity
                ? activityTime
                : _t("%(dateDeadline)s %(activityTime)s", {
                      dateDeadline: this.props.activity.dateDeadlineMED,
                      activityTime,
                  });
        }
    },
});
