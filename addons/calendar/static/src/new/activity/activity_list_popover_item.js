/** @odoo-module */

import { ActivityListPopoverItem } from "@mail/new/web/activity/activity_list_popover_item";
import { patch } from "@web/core/utils/patch";

patch(ActivityListPopoverItem.prototype, "calendar", {
    get hasEditButton() {
        return this._super() && !this.props.activity.calendar_event_id;
    },

    async onClickReschedule() {
        await this.env.services["mail.activity"].rescheduleMeeting(this.props.activity.id);
    },
});
