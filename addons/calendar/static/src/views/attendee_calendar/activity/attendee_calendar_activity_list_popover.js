import { AttendeeCalendarActivityListPopoverItem } from "@calendar/views/attendee_calendar/activity/attendee_calendar_activity_list_popover_item";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {number[]} activityIds
 * @property {Object} model
 * @property {function} close
 * @property {function} onActivityChanged
 * @extends {Component<Props, Env>}
 *
 * Highly inspired from the "ActivityListPopover" mail component.
 * Instead of managing the activities for a specific record (or specific selected records),
 * this component "activityIds" props refers to the user pending activities for a specific date.
 */
export class AttendeeCalendarActivityListPopover extends Component {
    static components = { Dialog, AttendeeCalendarActivityListPopoverItem };
    static props = ["activityIds", "model", "close", "onActivityChanged", "onViewMeeting"];
    static template = "calendar.AttendeeCalendarActivityListPopover";

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.limit = this.env.isSmall ? false : 5;

        onWillStart(async () => {
            const data = await this.orm.silent.call("mail.activity", "activity_format", [
                this.props.activityIds,
            ]);
            this.store.insert(data);
        });
    }

    /**
     * Fetch the activities from the store.
     * Each activity is an Activity js Record.
     */
    get activities() {
        /** @type {import("models").Activity[]} */
        return (this.limit ? this.props.activityIds.slice(0, this.limit) : this.props.activityIds)
            .map((id) => this.store["mail.activity"].get(id))
            .filter(Boolean); // Do not consider activities removed from the store
    }

    /**
     * Open the mail.activity views with the current popover activities.
     */
    async onClickViewAll() {
        const action = await this.action.loadAction("mail.mail_activity_action_my");
        action.context = { force_search_count: 1 }; // remove default search
        action.domain = [["id", "in", this.props.activityIds]];
        this.props.close();
        this.action.doAction(action);
    }

    /**
     * When an activity is removed from the popover (marked done, rescheduled, on file uploaded),
     * remove the activity id from the props to update the template and
     * automatically close the popover when there's no activity left.
     */
    onRemoveActivityItem(activityId) {
        this.props.activityIds = this.props.activityIds.filter((id) => id !== activityId);
        if (!this.props.activityIds.length) {
            this.props.close();
        }
    }
}
