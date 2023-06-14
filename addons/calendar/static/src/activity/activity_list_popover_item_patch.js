/** @odoo-module */

import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { patch } from "@web/core/utils/patch";
import { rescheduleMeeting } from "./activity_service_patch";

patch(ActivityListPopoverItem.prototype, "calendar", {
    get hasEditButton() {
        return this._super() && !this.props.activity.calendar_event_id;
    },

    async onClickReschedule() {
        await rescheduleMeeting(this.props.activity.id);
    },
});
