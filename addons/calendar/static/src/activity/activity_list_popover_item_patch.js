import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { patch } from "@web/core/utils/patch";

patch(ActivityListPopoverItem.prototype, {
    get hasEditButton() {
        return super.hasEditButton && !this.props.activity.calendar_event_id;
    },

    async onClickReschedule() {
        await this.props.activity.rescheduleMeeting();
    },
});
